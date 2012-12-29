organise-recordings
===================

Organise recordings (eg. from a digital voice recorder) by linking them to calendar events from an ical source.

Files from these recorders often come with incomprehensible file names and when you have a lot of recordings it is difficult to wade through them. This is especially a problem when the original file name does not include the date and time the recording was made.

This script relies on the file modification time of the original recording so it should be run against the files stored on the recorder.

Given an output directory and a path to an ical calendar file (may be at a remote URL to use with Google Calendar or similar) the script will copy files and rename them according to corresponding events. Where there are multiple (or no) events occuring around the time of the recording, the script will name the recording as 'uncategorised'. 
