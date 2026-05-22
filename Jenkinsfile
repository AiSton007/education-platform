// Jenkins pipeline for education-platform monorepo.
// Kubernetes-native build: no Docker daemon is required on Jenkins or cluster nodes.
// Required Jenkins credentials:
//   harbor-creds      - Username/password for Harbor robot account with push/pull to education-platform
//   github-deploy-ssh - SSH private key with write access to GitHub repo AiSton007/education-platform

pipeline {
  agent {
    kubernetes {
      defaultContainer 'python'
      yaml '''
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: jenkins-education-platform-build
spec:
  restartPolicy: Never
  containers:
    - name: python
      image: python:3.12-slim
      command: ['cat']
      tty: true
      resources:
        requests:
          cpu: 200m
          memory: 512Mi
        limits:
          cpu: '2'
          memory: 2Gi
    - name: node
      image: node:22-alpine
      command: ['cat']
      tty: true
      resources:
        requests:
          cpu: 100m
          memory: 256Mi
        limits:
          cpu: '1'
          memory: 1Gi
    - name: kaniko
      image: gcr.io/kaniko-project/executor:debug
      command: ['/busybox/cat']
      tty: true
      resources:
        requests:
          cpu: 250m
          memory: 512Mi
        limits:
          cpu: '2'
          memory: 2Gi
    - name: git
      image: alpine/git:2.45.2
      command: ['cat']
      tty: true
'''
    }
  }

  options {
    timeout(time: 45, unit: 'MINUTES')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '30'))
    skipDefaultCheckout(true)
  }

  environment {
    HARBOR = 'harbor.mokryakov.local:443'
    HARBOR_PROJECT = 'library'
    DEPLOY_REPO = 'git@github.com:AiSton007/education-platform.git'
    DEPLOY_BRANCH = 'master'
    VALUES_FILE = 'deploy/charts/education-platform/values.yaml'
  }

  stages {
    stage('Checkout') {
      steps {
        container('git') {
          checkout scm

          sh '''
            set -eux
            git config --global --add safe.directory "$WORKSPACE"
            mkdir -p ~/.ssh
            ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null || true
            git checkout -B "$DEPLOY_BRANCH"
          '''

          script {
            env.SHA = sh(
              returnStdout: true,
              script: 'git rev-parse --short HEAD'
            ).trim()

            env.LAST_COMMIT_MSG = sh(
              returnStdout: true,
              script: 'git log -1 --pretty=%s'
            ).trim()

            if (env.LAST_COMMIT_MSG.startsWith('ci: bump education-platform images')) {
              env.SKIP_PIPELINE = 'true'
              currentBuild.description = 'Skipped deploy-only image tag commit'
              echo 'Skipping build: this commit only updates Helm image tags.'
            } else {
              env.SKIP_PIPELINE = 'false'
            }

            echo "Building image tag: ${env.SHA}"
          }
        }
      }
    }

    stage('Install Python dependencies') {
      when { expression { env.SKIP_PIPELINE != 'true' } }
      steps {
        container('python') {
          sh '''
            set -eux
            apt-get update
            apt-get install -y --no-install-recommends build-essential libpq-dev curl ca-certificates git
            rm -rf /var/lib/apt/lists/*
            pip install --no-cache-dir uv==0.5.4
            uv --version
            uv sync --all-extras
          '''
        }
      }
    }

    stage('Lint') {
      when { expression { env.SKIP_PIPELINE != 'true' } }
      parallel {
        stage('Python lint') {
          steps {
            container('python') {
              sh 'uv run ruff check .'
              sh 'uv run ruff format --check .'
            }
          }
        }

        stage('Frontend lint') {
          when { expression { fileExists('frontend/package.json') } }
          steps {
            container('node') {
              dir('frontend') {
                sh '''
                  set -eux
                  if [ -f package-lock.json ]; then
                    npm ci --no-audit --no-fund
                  else
                    npm install --no-audit --no-fund
                  fi
                  npm run lint
                '''
              }
            }
          }
        }
      }
    }

    stage('Test') {
      when { expression { env.SKIP_PIPELINE != 'true' } }
      steps {
        container('python') {
          sh 'uv run pytest -q --maxfail=1'
        }
      }
    }

    stage('Prepare Harbor auth for Kaniko') {
      when { expression { env.SKIP_PIPELINE != 'true' } }
      steps {
        container('kaniko') {
          withCredentials([usernamePassword(credentialsId: 'harbor-creds', usernameVariable: 'HARBOR_USER', passwordVariable: 'HARBOR_PASS')]) {
            sh '''
              set -eu
              mkdir -p /kaniko/.docker
              AUTH=$(printf "%s:%s" "$HARBOR_USER" "$HARBOR_PASS" | base64 | tr -d '\n')
              cat > /kaniko/.docker/config.json <<EOF_AUTH
{"auths":{"$HARBOR":{"auth":"$AUTH"}}}
EOF_AUTH
            '''
          }
        }
      }
    }

    stage('Build & push backend images') {
      when { expression { env.SKIP_PIPELINE != 'true' } }
      steps {
        container('kaniko') {
          sh '''
            set -eux
            services="auth_service user_service test_service llm_service report_service api_gateway"

            for service in $services; do
              image_name=$(echo "$service" | tr '_' '-')

              /kaniko/executor \
                --context "$WORKSPACE" \
                --dockerfile "$WORKSPACE/Dockerfile" \
                --build-arg SERVICE="$service" \
                --destination "$HARBOR/$HARBOR_PROJECT/$image_name:$SHA" \
                --cache=true \
                --cache-repo "$HARBOR/$HARBOR_PROJECT/cache" \
                --skip-tls-verify-registry "$HARBOR"

              if [ "$service" != "api_gateway" ]; then
                /kaniko/executor \
                  --context "$WORKSPACE" \
                  --dockerfile "$WORKSPACE/Dockerfile.migrate" \
                  --build-arg SERVICE="$service" \
                  --destination "$HARBOR/$HARBOR_PROJECT/$image_name-migrate:$SHA" \
                  --cache=true \
                  --cache-repo "$HARBOR/$HARBOR_PROJECT/cache" \
                  --skip-tls-verify-registry "$HARBOR"
              fi
            done
          '''
        }
      }
    }

    stage('Build & push frontend image') {
      when {
        allOf {
          expression { env.SKIP_PIPELINE != 'true' }
          expression { fileExists('frontend/Dockerfile') }
        }
      }
      steps {
        container('kaniko') {
          sh '''
            set -eux
            /kaniko/executor \
              --context "$WORKSPACE/frontend" \
              --dockerfile "$WORKSPACE/frontend/Dockerfile" \
              --build-arg VITE_API_URL=https://api.mokryakov.local \
              --destination "$HARBOR/$HARBOR_PROJECT/frontend:$SHA" \
              --cache=true \
              --cache-repo "$HARBOR/$HARBOR_PROJECT/cache" \
              --skip-tls-verify-registry "$HARBOR"
          '''
        }
      }
    }

    stage('Update Helm image tags') {
      when { expression { env.SKIP_PIPELINE != 'true' } }
      steps {
        container('python') {
          sh '''
            set -eux
            python - <<'PY'
import os
from pathlib import Path

path = Path('deploy/charts/education-platform/values.yaml')
sha = os.environ['SHA']
text = path.read_text()

# The chart is expected to store image tags as YAML lines named "tag:".
# All image tags are bumped to the current short commit SHA.
lines = text.splitlines()
out = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith('tag: '):
        indent = line[:len(line) - len(line.lstrip())]
        out.append(f'{indent}tag: {sha}')
    else:
        out.append(line)
path.write_text('\n'.join(out) + '\n')
PY
            git diff -- deploy/charts/education-platform/values.yaml
          '''
        }
      }
    }

    stage('Push updated values.yaml') {
      when { expression { env.SKIP_PIPELINE != 'true' } }
      steps {
        container('git') {
          withCredentials([sshUserPrivateKey(credentialsId: 'github-deploy-ssh', keyFileVariable: 'GIT_SSH_KEY')]) {
            sh '''
              set -eux
              git config --global --add safe.directory "$WORKSPACE"
              git config user.email "jenkins@mokryakov.local"
              git config user.name "Jenkins"

              mkdir -p ~/.ssh
              ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null || true
              chmod 700 ~/.ssh

              git remote set-url origin "$DEPLOY_REPO"
              git add "$VALUES_FILE"

              if git diff --cached --quiet; then
                echo "No Helm image tag changes to commit."
                exit 0
              fi

              git commit -m "ci: bump education-platform images to $SHA"
              GIT_SSH_COMMAND="ssh -i $GIT_SSH_KEY -o UserKnownHostsFile=$HOME/.ssh/known_hosts" \
                git push origin HEAD:"$DEPLOY_BRANCH"
            '''
          }
        }
      }
    }
  }

  post {
    always {
      echo "Pipeline finished with result: ${currentBuild.currentResult}"
    }
    success {
      echo 'Build completed successfully'
    }
    failure {
      echo 'Build failed. Check the first real ERROR/fatal line above in Console Output.'
    }
  }
}
