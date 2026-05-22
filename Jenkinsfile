// Declarative Jenkins pipeline for the Python monorepo.
//
// Required Jenkins credentials:
//   harbor-creds          (username/password)            — Harbor docker registry
//   deploy-repo-ssh       (SSH private key)              — github/gitea push access
//   gigachat-api-key      (secret text, optional)        — only for env-promote stage
//
// Tags use the short git SHA. The deploy-repo's values.yaml gets updated and pushed,
// ArgoCD picks the change up automatically and runs the migrate Jobs as PreSync hooks.

pipeline {
  agent any
  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '50'))
  }
  environment {
    HARBOR        = 'harbor.mokryakov.local'
    HARBOR_PROJ   = 'education-platform'
    DEPLOY_REPO   = 'git@harbor.mokryakov.local:platform/education-platform-deploy.git'
    DEPLOY_BRANCH = 'main'
    PYTHON_VERSION = '3.12'
  }
  stages {
    stage('Checkout') {
      steps {
        checkout scm
        script {
          env.SHA = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
        }
        echo "Building tag ${env.SHA}"
      }
    }

    stage('Setup uv') {
      steps {
        sh '''
          set -euo pipefail
          if ! command -v uv >/dev/null 2>&1; then
            pip install --user uv==0.5.4
            export PATH="$HOME/.local/bin:$PATH"
          fi
          uv --version
          uv sync --all-extras
        '''
      }
    }

    stage('Lint') {
      parallel {
        stage('Python lint') {
          steps {
            sh 'uv run ruff check .'
            sh 'uv run ruff format --check .'
          }
        }
        stage('Frontend lint') {
          steps {
            dir('frontend') {
              sh 'npm ci --no-audit --no-fund'
              sh 'npm run lint'
            }
          }
        }
      }
    }

    stage('Test') {
      steps {
        sh 'uv run pytest -q --maxfail=1'
      }
    }

    stage('Build & push images') {
      environment {
        TAG = "${env.SHA}"
      }
      steps {
        withCredentials([usernamePassword(credentialsId: 'harbor-creds',
                                          usernameVariable: 'HUSR',
                                          passwordVariable: 'HPWD')]) {
          sh '''
            set -euo pipefail
            echo "$HPWD" | docker login "$HARBOR" -u "$HUSR" --password-stdin

            services="auth_service user_service test_service llm_service report_service api_gateway"
            for s in $services; do
              name=$(echo "$s" | tr '_' '-')
              echo "==> building $name"
              docker buildx build \
                --build-arg SERVICE="$s" \
                -t "$HARBOR/$HARBOR_PROJ/$name:$TAG" \
                -f Dockerfile --push .
              if [ "$s" != "api_gateway" ]; then
                docker buildx build \
                  --build-arg SERVICE="$s" \
                  -t "$HARBOR/$HARBOR_PROJ/$name-migrate:$TAG" \
                  -f Dockerfile.migrate --push .
              fi
            done

            docker buildx build \
              -t "$HARBOR/$HARBOR_PROJ/frontend:$TAG" \
              -f frontend/Dockerfile --push frontend
          '''
        }
      }
    }

    stage('Update deploy-repo') {
      steps {
        sshagent (credentials: ['deploy-repo-ssh']) {
          sh '''
            set -euo pipefail
            rm -rf .deploy
            git clone "$DEPLOY_REPO" .deploy
            cd .deploy
            git checkout "$DEPLOY_BRANCH"
            git config user.email "jenkins@mokryakov.local"
            git config user.name  "Jenkins"

            for svc in auth-service user-service test-service llm-service report-service api-gateway frontend; do
              yq -i ".services.\"$svc\".image.tag = \"$SHA\"" charts/education-platform/values.yaml || true
            done
            for svc in auth-service user-service test-service llm-service report-service; do
              yq -i ".services.\"$svc\".migrate.image.tag = \"$SHA\"" charts/education-platform/values.yaml || true
            done

            git add charts/education-platform/values.yaml
            git diff --cached --quiet || git commit -m "ci: bump education-platform to ${SHA}"
            git push origin "$DEPLOY_BRANCH"
          '''
        }
      }
    }
  }
  post {
    always {
      junit allowEmptyResults: true, testResults: 'reports/junit/**/*.xml'
    }
    failure {
      echo "Build failed at ${env.STAGE_NAME}"
    }
  }
}
