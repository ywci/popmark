# Popmark - A Distributed Tester Framework

## **Quick Start**

#### Installation

* Run `./install.sh` to install Popmark.

#### Configuration

* Please check the files in the "conf" directory.
  1. The tester settings are contained in "conf/popmark.py".
  2. The workloads are specified in "conf/workload.py".

* Popmark has three roles: **server**, **client**, and **runner**. It is important to launch the servers first, followed by the clients. Finally, start the runners, which are deployed on the client side to provide additional workloads. Please note that the configuration must specify at least one role to ensure proper functioning of Popmark.

#### Running Tests

* Execute `./run.sh` to run all tests specified in "conf/workloads.py".

#### Testing

* Use `./run.sh --test` to perform a test using the workload specified in "scripts/ex_workload.py".
* "scripts/ex_conf.py" can configure Popmark to run tests in standalone mode.

#### Results

* The test results are stored in the "outputs" directory.

## **Version**

* Current version is 0.1

## **License**

* Popmark is released under the terms of the MIT License.
