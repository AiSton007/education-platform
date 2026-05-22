// Jenkins pipeline for education-platform monorepo.
// Kubernetes-native build: no Docker daemon is required on Jenkins or cluster nodes.
// Required Jenkins credentials:
//   harbor-creds    - Username/password for Harbor robot account with push/pull to education-platform
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
    timestamps()
    timeout(time: 45, unit: 'MINUTES')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '30'))
    skipDefaultCheckout(true)
  }

  environment {
    HARBOR = 'harbor.mokryakov.local:443'
    HARBOR_PROJECT = 'education-platform'
    DEPLOY_REPO = 'https://github.com/AiSton007/education-platform.git'
    DEPLOY_BRANCH = 'master'
    VALUES_FILE = 'deploy/charts/education-platform/values.yaml'
  }

  stage('Checkout') {
  steps {
    container('git') {
      checkout scm

      sh '''
        git config --global --add safe.directory "$WORKSPACE"
        mkdir -p ~/.ssh
        ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null || true
      '''

      script {
        env.SHA = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
        env.LAST_COMMIT_MSG = sh(returnStdout: true, script: 'git log -1 --pretty=%s').trim()

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
                sh 'npm ci --no-audit --no-fund'
                sh 'npm run lint'
              }
            }
          }
        }
      }
    }

    stage('Test') {
      steps {
        container('python') {
          sh 'uv run pytest -q --maxfail=1'
        }
      }
    }

    stage('Prepare Harbor auth for Kaniko') {
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
      when { expression { fileExists('frontend/Dockerfile') } }
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
      steps {
        container('python') {
          sh '''
            set -eux
            python - <<'PY'
from pathlib import Path

path = Path('deploy/charts/education-platform/values.yaml')
text = path.read_text()
sha = '${SHA}'

# This simple updater expects every service/frontend image block to contain "tag: ...".
# It replaces all chart image tags with the current commit SHA.
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
      steps {
        container('git') {
          sshagent(credentials: ['github-deploy-ssh']) {
            sh '''
              set -eux
              git config user.email "jenkins@mokryakov.local"
              git config user.name "Jenkins"

              git remote set-url origin "$DEPLOY_REPO"
              git checkout "$DEPLOY_BRANCH"
              git add "$VALUES_FILE"
              git diff --cached --quiet && exit 0
              git commit -m "ci: bump education-platform images to $SHA"
              git push origin "$DEPLOY_BRANCH"
            '''
          }
        }
      }
    }
  }

  post {
    always {
        echo "Pipeline finished"
    }
    success {
        echo "Build completed successfully"
    }
    failure {
        echo "Build failed at stage: ${env.STAGE_NAME}"
    }
  }
}