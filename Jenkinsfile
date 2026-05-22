// Jenkins pipeline for education-platform monorepo.
// Kubernetes-native build: no Docker daemon is required on Jenkins or cluster nodes.
// Required Jenkins credentials:
//   harbor-creds      - Username/password for Harbor robot account with push/pull to the configured Harbor project
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
    HARBOR = 'harbor.mokryakov.local'
    HARBOR_SCHEME = 'http'
    HARBOR_PORT = '80'
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


    stage('Preflight: repository layout') {
      when { expression { env.SKIP_PIPELINE != 'true' } }
      steps {
        container('git') {
          sh '''
            set -eux
            test -f Jenkinsfile
            test -f Dockerfile
            test -f Dockerfile.migrate
            test -f "$VALUES_FILE"
            test -d services/auth_service
            test -d services/user_service
            test -d services/test_service
            test -d services/llm_service
            test -d services/report_service
            test -d services/api_gateway

            if [ -d frontend ]; then
              test -f frontend/package.json
              test -f frontend/Dockerfile
            fi
          '''
        }
      }
    }

    stage('Preflight: infrastructure access') {
      when { expression { env.SKIP_PIPELINE != 'true' } }
      steps {
        container('python') {
          withCredentials([usernamePassword(credentialsId: 'harbor-creds', usernameVariable: 'HARBOR_USER', passwordVariable: 'HARBOR_PASS')]) {
            sh '''
              set -eu
              python - <<'PY'
import base64
import os
import socket
import ssl
import urllib.error
import urllib.request

harbor = os.environ['HARBOR']
project = os.environ['HARBOR_PROJECT']
user = os.environ['HARBOR_USER']
password = os.environ['HARBOR_PASS']

scheme = os.environ.get('HARBOR_SCHEME', 'http').lower()
if ':' in harbor:
    host, port_raw = harbor.rsplit(':', 1)
    port = int(port_raw)
else:
    host = harbor
    port = int(os.environ.get('HARBOR_PORT') or (443 if scheme == 'https' else 80))

print(f'[CHECK] Harbor DNS: {host}')
try:
    addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
except socket.gaierror as exc:
    raise SystemExit(f'[FAIL] Harbor DNS resolution failed for {host}: {exc}') from exc
print(f'[OK] Harbor resolves to: {", ".join(addresses)}')

print(f'[CHECK] Harbor TCP: {host}:{port}')
try:
    with socket.create_connection((host, port), timeout=8):
        pass
except OSError as exc:
    raise SystemExit(f'[FAIL] Cannot connect to Harbor {host}:{port}: {exc}') from exc
print('[OK] Harbor TCP connection works')

ctx = ssl._create_unverified_context()
base_url = f'{scheme}://{harbor}'

def request(path: str, auth: bool = False) -> int:
    req = urllib.request.Request(base_url + path)
    if auth:
        token = base64.b64encode(f'{user}:{password}'.encode()).decode()
        req.add_header('Authorization', f'Basic {token}')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=12) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception as exc:
        raise SystemExit(f'[FAIL] HTTP request to {base_url}{path} failed: {exc}') from exc

print('[CHECK] Harbor registry API: /v2/')
status = request('/v2/')
if status not in (200, 401):
    raise SystemExit(f'[FAIL] Unexpected Harbor /v2/ status: {status}, expected 200 or 401')
print(f'[OK] Harbor /v2/ reachable, status={status}')

print('[CHECK] Harbor robot credentials against registry API: /v2/')
status = request('/v2/', auth=True)
if status not in (200,):
    raise SystemExit(
        f'[FAIL] Harbor robot credentials check failed, status={status}. '
        'Check credential harbor-creds: username must be robot$library+jenkins and password must be the robot secret/token.'
    )
print('[OK] Harbor robot credentials accepted by registry API')

print(f'[CHECK] Harbor project API visibility: {project}')
status = request(f'/api/v2.0/projects/{project}', auth=True)
if status == 200:
    print('[OK] Harbor project API is visible to this credential')
elif status == 403:
    print(
        '[WARN] Harbor project API returned 403 for the robot account. '
        'This is acceptable for some Harbor robot accounts. The pipeline will continue; Kaniko push will be the real push-permission check.'
    )
elif status == 404:
    raise SystemExit(f'[FAIL] Harbor project "{project}" was not found by Harbor API, status=404')
else:
    print(f'[WARN] Harbor project API returned unexpected status={status}. Continuing to Kaniko push check.')
PY
            '''
          }
        }

        container('git') {
          withCredentials([sshUserPrivateKey(credentialsId: 'github-deploy-ssh', keyFileVariable: 'GIT_SSH_KEY')]) {
            sh '''
              set -eu
              mkdir -p ~/.ssh
              ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null || true
              chmod 700 ~/.ssh
              chmod 600 "$GIT_SSH_KEY" 2>/dev/null || true

              echo "[CHECK] GitHub SSH deploy key access to $DEPLOY_REPO"
              set +e
              OUT=$(GIT_SSH_COMMAND="ssh -i $GIT_SSH_KEY -o IdentitiesOnly=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts" \
                git ls-remote "$DEPLOY_REPO" HEAD 2>&1)
              RC=$?
              set -e
              echo "$OUT"

              if [ "$RC" -eq 0 ]; then
                echo "[OK] GitHub SSH deploy key can read the repository"
              else
                echo "[WARN] GitHub SSH deploy key check failed with rc=$RC"
                echo "[WARN] This preflight check is non-critical and the pipeline will continue."
                echo "[WARN] The final stage 'Push updated values.yaml' may still fail if github-deploy-ssh has no write access."
              fi
            '''
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
            # Increase sync timeout and retry transient network failures.
            # "timeout" keeps the stage from hanging forever on package index calls.
            max_attempts=4
            attempt=1
            while [ "$attempt" -le "$max_attempts" ]; do
              echo "uv sync attempt ${attempt}/${max_attempts}"
              if timeout 20m uv sync --all-extras; then
                echo "uv sync succeeded"
                break
              fi

              if [ "$attempt" -eq "$max_attempts" ]; then
                echo "uv sync failed after ${max_attempts} attempts"
                exit 1
              fi

              sleep_seconds=$((attempt * 20))
              echo "uv sync failed, retrying in ${sleep_seconds}s..."
              sleep "$sleep_seconds"
              attempt=$((attempt + 1))
            done
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
                --skip-tls-verify-registry "$HARBOR" \
                --insecure-registry "$HARBOR"

              if [ "$service" != "api_gateway" ]; then
                /kaniko/executor \
                  --context "$WORKSPACE" \
                  --dockerfile "$WORKSPACE/Dockerfile.migrate" \
                  --build-arg SERVICE="$service" \
                  --destination "$HARBOR/$HARBOR_PROJECT/$image_name-migrate:$SHA" \
                  --cache=true \
                  --cache-repo "$HARBOR/$HARBOR_PROJECT/cache" \
                  --skip-tls-verify-registry "$HARBOR" \
                --insecure-registry "$HARBOR"
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
              --skip-tls-verify-registry "$HARBOR" \
                --insecure-registry "$HARBOR"
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
            cd "$WORKSPACE"
            test -d .git || { echo "[FAIL] .git directory was not found in $WORKSPACE"; exit 2; }
            git config --global --add safe.directory "$WORKSPACE"
            test -f "$VALUES_FILE"

            python - <<'PY'
import os
from pathlib import Path

path = Path(os.environ['VALUES_FILE'])
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
path.write_text('\\n'.join(out) + '\\n')
PY
            git -C "$WORKSPACE" diff -- "$VALUES_FILE" || true
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
              cd "$WORKSPACE"
              test -d .git || { echo "[FAIL] .git directory was not found in $WORKSPACE"; exit 2; }
              test -f "$VALUES_FILE"

              git config --global --add safe.directory "$WORKSPACE"
              git config user.email "jenkins@mokryakov.local"
              git config user.name "Jenkins"

              mkdir -p ~/.ssh
              ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null || true
              chmod 700 ~/.ssh
              chmod 600 "$GIT_SSH_KEY" 2>/dev/null || true

              git remote set-url origin "$DEPLOY_REPO"
              git add "$VALUES_FILE"

              if git diff --cached --quiet; then
                echo "No Helm image tag changes to commit."
                exit 0
              fi

              git commit -m "ci: bump education-platform images to $SHA"
              GIT_SSH_COMMAND="ssh -i $GIT_SSH_KEY -o IdentitiesOnly=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts" \
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
