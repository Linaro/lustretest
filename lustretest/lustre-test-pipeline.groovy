pipeline {
    agent {
        label 'lustre-test-agent'
    }

    environment {
        CUMULATIVE_RESULT_ID = UUID.randomUUID().toString()
        LUSTRE_BRANCH = "master"
    }

    stages {
        stage('Cleanup workspace') {
            steps {
                sh 'ls -l ${WORKSPACE}'
                sh 'rm -fr *'
                sh 'ln -sf /home/centos/workspace/nfs/test_logs ${WORKSPACE}/test_logs'
            }
        }
        stage('Build') {
            steps {
                echo 'Building..'
                /* 
                build job: 'project-lustre-build-release-master',
                    parameters: [
                    string(name: 'BRANCH', value: ${LUSTRE_BRANCH}),
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
        stage('Test Execution'){
            parallel {
                /* Usage: test_runner.py <arg1> <arg2> [arg3]
                 * arg1: <TEST_GROUP_ID> test group id wich is 1-6
                 * arg2: <PROVISION_NEW_CLUSTER> True or Flase
                 * arg3: [DESTROY_CLUSTER] True or False for provision new cluster
                 */
                stage('Run test group 1') {
                    steps {
                        dir("lustretest-main/lustretest") {
                            sh 'source /home/centos/venv3/bin/activate;python3 test_runner.py 1 False'
                        }
                    }
                }
                stage('Run test group 2') {
                    steps {
                        dir("lustretest-main/lustretest") {
                            sh 'source /home/centos/venv3/bin/activate;python3 test_runner.py 2 False'
                        }
                    }
                }
                stage('Run test group 3') {
                    steps {
                        dir("lustretest-main/lustretest") {
                            sh 'source /home/centos/venv3/bin/activate;python3 test_runner.py 3 False'
                        }
                    }
                }
            }
        }
    }
}
