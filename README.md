# Singing Boxes: An Autonomous and Adaptive Leader-Follower Protocol for Collaborative Robotics
[Demo Video](https://drive.google.com/file/d/1nrH9m9OET4b8nIUntWM6QS8P7RI4sD1G/view?usp=sharing "https://drive.google.com/file/d/1nrH9m9OET4b8nIUntWM6QS8P7RI4sD1G/view?usp=sharing")

In this short demo, five devices communicate wirelessly to each play a different track of "Piano Man."  The leader will assign a task to all connected devices as they join and transmit indicators to synchronize actions in real-time. When the leader (red) is manually disconnected, a follower (blue) seamlessly takes over as the new leader. When a follower is disconnected, its task becomes available to any new devices that join, as coordinated by the leader. You can hear the different tracks stop as I disconnect a device, and start in synchronization with the others as I reconnect it. The screen of each device details its leader/follower status, as well as the track it is currently playing.

The protocol uses a probabilistic framework and an object-oriented design to coordinate a mesh network of devices. One leader is selected and will add any other devices as followers, distribute tasks amongst them, and monitor their status. It is designed for resiliency, so that if any device disconnects, even the leader, the collective remains intact.

![alt text](https://github.com/dhilanpatel26/singing_boxes/blob/main/simulations/sb_protocol_diagram.png "Protocol Block Diagram")

The communication occurs over radio frequency at 433MHz using a CC1101 transceiver. The protocol is designed to be functional with other communication methods such as Wi-Fi or infrared, and generalizable to any number of devices or tasks.

The robustness of the control system's communication protocol also allows for follower-leader feedback, dynamic message payloads, and the prioritization of available roles. Alongside an increased number of devices, these features enable for the parallelization and execution of more complex tasks. The speed of this algorithm is only limited by the transmission and receiving capabilities of devices at 433MHz. In addition, time complexity of the check-in process scales linearly with the number of devices in the network. This protocol has applications for collaborative tasks in various industries, such as agriculture, construction, and defense -- really any sector that requires coordinated tasks to be completed simultaneously.

![alt text](https://github.com/dhilanpatel26/singing_boxes/blob/main/simulations/sb_simulations.jpg "Simulation Plots")
