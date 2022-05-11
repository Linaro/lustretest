pipeline {
    agent {
        label 'lustre-test-agent'
    }

    environment {
        CUMULATIVE_RESULT_ID = UUID.randomUUID().toString()
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
        stage('Test Execution'){
            parallel {
                stage('Test Suites 1'){
                    stages{
                        stage('Provision test cluster 1') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 provision.py 1 False lustre-wleilf4j'
                                }
                            }
                        }
                        stage('Cluster nodes init 1') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 1'
                                }
                            }
                        }
                        stage('Run test suites 1') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 1 True'
                                }
                            }
                        }
                        stage('Cluster nodes init 4') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 4'
                                }
                            }
                        }
                        stage('Run test suites 4') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 4 True'
                                }
                            }
                        }
                    }
                }
                stage('Test Suites 2'){
                    stages{
                        stage('Provision test cluster 2') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 provision.py 2 False lustre-ghbemii7'
                                }
                            }
                        }
                        stage('Cluster nodes init 2') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 2'
                                }
                            }
                        }
                        stage('Run test suites 2') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 2 True'
                                }
                            }
                        }
                        stage('Client node init 5') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 5'
                                }
                            }
                        }
                        stage('Run test suites 5') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 5 True'
                                }
                            }
                        }
                    }
                }
                stage('Test Suites 3'){
                    stages{
                        stage('Provision test cluster 3') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 provision.py 3 False lustre-wujqyzn6'
                                }
                            }
                        }
                        stage('Cluster nodes init 3') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 3'
                                }
                            }
                        }
                        stage('Run test suites 3') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 3 True'
                                }
                            }
                        }
                        stage('Client node init 6') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 6'
                                }
                            }
                        }
                        stage('Run test suites 6') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 6 True'
                                }
                            }
                        }
                    }

                }
            }
        }

    }
}
