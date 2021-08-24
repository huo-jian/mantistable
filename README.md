## MantistTable Tool

We have 4 implementations of MantisTable developed over time:

1. https://bitbucket.org/disco_unimib/mantistable-tool/
here there is our first implementation in Meteor/NodeJS.
In this version we faced some scalability issues so it was later reimplemented from scratch.

2. https://bitbucket.org/disco_unimib/mantistable-tool.py
The second version is a more computationally efficient version in python

3. While the 3rd version is the one used during the SemTab 2019 Challenge
https://bitbucket.org/disco_unimib/mantistable-tool-3
(This repository, current up to date implementation)

4. The 4th version is a new implementation with a new algorithm that we are currently testing on SemTab2020,
for now is not ready for release, we will probably publish it by the end of the year, it will be called MantisTable SE.


## How to run MantisTable:

The first step consists in installing the required dependencies
    `npm install`
(Node 8+ is required with an updated npm version)

We used docker-compose from the beginning, so in order to run any version of MantisTable it's enough to use the command:
    `docker-compose up`

inside the docker-compose.yml file you will find the ports where the service will start
(actually port 8007 but it can be customized)
on line 38 replace "16" in "--autoscale=16,4" with the number of available Cores on your Server.

## Demo:
On [http://zoo.disco.unimib.it](http://zoo.disco.unimib.it) we have the main information about our tools and there is a link to a running demo of the 3rd version [http://149.132.176.50:8092](http://149.132.176.50:8092) 