pipeline {
    agent any
    environment {
        region = 'ap-south-1'
        containerFamily = 'vaani'
        newimage = ""
        serviceName = "vaani"
        accountId = "370531249777"
    }

    stages {
        stage('Docker build') {
            when { not { branch "feature*" } }
            environment {
                image = "${env.accountId}.dkr.ecr.ap-south-1.amazonaws.com/vaani:${env.BRANCH_NAME}-${env.BUILD_ID}"
            }
            steps {
                script {
                    docker.withRegistry("https://${env.accountId}.dkr.ecr.ap-south-1.amazonaws.com") {
                        def customImage = docker.build("${env.accountId}.dkr.ecr.ap-south-1.amazonaws.com/vaani:${env.BRANCH_NAME}-${env.BUILD_ID}")
                        customImage.push()
                    }
                }
            }
        }

        stage("Create Task, Deploy - Server") {
            when {
                anyOf {
                    branch "release"
                    branch "master"
                }
            }
            environment {
                newimage = "${env.accountId}.dkr.ecr.${env.region}.amazonaws.com/${env.containerFamily}:${env.BRANCH_NAME}-${env.BUILD_ID}"
            }
            steps {
                script {
                    if (env.BRANCH_NAME == "release") {
                        env.clusterName = "gamma-amd"
                        env.stage = "gamma"
                        env.taskDefFile = "task-def-server.json"
                        sh "/var/lib/jenkins/worker-scripts/create-new-task-def.sh"
                        sh "/var/lib/jenkins/worker-scripts/trigger_deploy.sh"
                    }

                    // if (env.BRANCH_NAME == "master") {
                    //     env.clusterName = "prod-amd"
                    //     env.stage = "prod"
                    //     env.taskDefFile = "task-def-server.json"
                    //     sh "/var/lib/jenkins/worker-scripts/create-new-task-def.sh"
                    //     sh "/var/lib/jenkins/worker-scripts/trigger_deploy.sh"
                    // }
                }
                sh "git tag -a ${clusterName}_${serviceName}_${BUILD_ID} -m \"tagging ${stage}-${BUILD_ID} \""
                sh "git push --tags"
            }
        }

        stage("Create Task, Deploy - Worker") {
            when {
                anyOf {
                    branch "release"
                    branch "master"
                }
            }
            environment {
                newimage = "${env.accountId}.dkr.ecr.${env.region}.amazonaws.com/${env.containerFamily}:${env.BRANCH_NAME}-${env.BUILD_ID}"
            }
            steps {
                script {
                    if (env.BRANCH_NAME == "release") {
                        env.clusterName = "gamma-worker-amd"
                        env.stage = "gamma"
                        env.taskDefFile = "task-def-worker.json"
                        sh "/var/lib/jenkins/worker-scripts/create-new-task-def.sh"
                        sh "/var/lib/jenkins/worker-scripts/trigger_deploy.sh"
                    }

                    // if (env.BRANCH_NAME == "master") {
                    //     env.clusterName = "prod-worker-amd"
                    //     env.stage = "prod"
                    //     env.taskDefFile = "task-def-worker.json"
                    //     sh "/var/lib/jenkins/worker-scripts/create-new-task-def.sh"
                    //     sh "/var/lib/jenkins/worker-scripts/trigger_deploy.sh"
                    // }
                }
                sh "git tag -a ${clusterName}_${serviceName}_${BUILD_ID} -m \"tagging ${stage}-${BUILD_ID} \""
                sh "git push --tags"
            }
        }
    }
}
