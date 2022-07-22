A quick tool for getting basic statistics on logs from https://www.pokernow.club/

Usage:

python3 log_processor.py logs/

Warnings may be emitted when new log formats are introduced, which can prevent results from being printed. At this point, you have two options:

1) Update the tool to handle the new log format. This would be greatly appreciated on my end :) 
2) Use the flag --ignore_warnings. This will ignore any lines in the log that haven't been explicitly handled. Of course, if these lines related to the stats, you'll get more inaccurate results. 

If you want to help extend capabilities, have bug reports, or feature requests, let me know. I will do my best to address these in the time that I have.
