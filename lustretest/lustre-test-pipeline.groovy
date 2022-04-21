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
                    sh 'source /home/centos/venv3/bin/activate;python3 provision.py'
                }
            }
        }
        stage('Client node init') {
            steps {
                dir("lustretest-main/lustretest") {
                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py'
                }
            }
        }
        stage('Run test') {
            steps {
                dir("lustretest-main/lustretest") {
                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py'
                }
            }
        }
    }
}
