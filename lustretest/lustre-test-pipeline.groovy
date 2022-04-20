pipeline {
    agent {
        label 'lustre-test-agent'
    }

    stages {
        stage('Cleanup workspace') {
            steps {
                sh 'ls -l ${WORKSPACE}'
                sh 'rm -fr *'
            }
        }
        stage('Build') {
            steps {
                echo 'Building..'
                /* 
                build job: 'project-lustre-build-release-master',
                    parameters: [string(name: 'BRANCH', value: 'master'),
                    string(name: 'BUILD_LINUX', value: 'yes')]
                */
            }
        }
        stage('Download scripts') {
            steps {
                sh 'wget -c https://github.com/Linaro/lustretest/archive/refs/heads/main.zip'
                sh 'unzip main.zip'
            }
        }
        stage('Provision test excution nodes') {
            steps {
                dir("lustretest-main/lustretest") {
                    //sh 'python3 provision.py'
                    sh 'ls -l'
                    sh 'python3 --version'
                }
            }
        }
        stage('Client node init') {
            steps {
                dir("lustretest-main/lustretest") {
                    //sh 'python3 node_init.py'
                    sh 'ls -l'
                    sh 'python3 --version'
                }
            }
        }
        stage('Run test') {
            steps {
                dir("lustretest-main/lustretest") {
                    sh 'ls -l'
                    sh 'python3 --version'
                }
            }
        }
        stage('Upload test results to maloo DB') {
            steps {
                echo 'upload test results....'
            }
        }
    }
}
