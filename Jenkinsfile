pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "suivi-ftth-app"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    echo "Construction de l'image Docker..."
                    sh "docker build -t ${DOCKER_IMAGE}:${env.BUILD_ID} ."
                    sh "docker tag ${DOCKER_IMAGE}:${env.BUILD_ID} ${DOCKER_IMAGE}:latest"
                }
            }
        }

        stage('Deploy with Docker Compose') {
            steps {
                script {
                    echo "Déploiement de l'application..."
                    // On down d'abord (optionnel, permet un redémarrage propre)
                    sh "docker compose down"
                    // On lance en mode détaché
                    sh "docker compose up -d --build"
                }
            }
        }
    }

    post {
        success {
            echo "Déploiement réussi ! L'application tourne sur le port 5000."
        }
        failure {
            echo "Le déploiement a échoué. Veuillez vérifier les logs."
        }
    }
}
