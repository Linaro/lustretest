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
        stage('Test Execution'){
            parallel {
                stage('Test Suites 1'){
                    stages{
                        stage('Provision test excution nodes') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 provision.py 1 False lustre-wleilf4j'
                                }
                            }
                        }
                        stage('Client node init') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 1'
                                }
                            }
                        }
                        stage('Run test') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 1'
                                }
                            }
                        }
                    }
                }
                stage('Test Suites 2'){
                    stages{
                        stage('Provision test excution nodes') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 provision.py 2 False lustre-ghbemii7'
                                }
                            }
                        }
                        stage('Client node init') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 2'
                                }
                            }
                        }
                        stage('Run test') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 2'
                                }
                            }
                        }
                    }
                }
                stage('Test Suites 3'){
                    stages{
                        stage('Provision test excution nodes') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 provision.py 3 False lustre-wujqyzn6'
                                }
                            }
                        }
                        stage('Client node init') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 node_init.py 3'
                                }
                            }
                        }
                        stage('Run test') {
                            steps {
                                dir("lustretest-main/lustretest") {
                                    sh 'source /home/centos/venv3/bin/activate;python3 auster.py 3'
                                }
                            }
                        }
                    }

                }
            }
        }

    }
}
