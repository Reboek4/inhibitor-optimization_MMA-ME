Here is a small cheatsheet for the usage and the files.

INFO: .pkl files are something like a zip files that can be used to transfer data between different scripts.
They can not be used to view the data
INFO: to view or export the data that were generated from the "last run" .csv files can be used.

How to run:

1) If you have a new dataset run the nodes_data.py script to update your data within the working space.
2) Run metrics_to_script.py to get your new delta and c1_alpha values
 - you can adjust your punishment variable and choose to add/remove datapoints inside this
3) Run optimization.py to train and get generate expected values from your model
 -adjust weights of the objective functions to get "best experimental conditions".


