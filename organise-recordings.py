import argparse
import logging
from icalendar import Calendar, Event
from dateutil.rrule import rrulestr
import dateutil
import datetime
import pytz
import os
import shutil

# Read calendar from ical and get times and event names
def get_calendar_tuples(calFile):
    fp = open(calFile, 'r')
    icalStr = "".join(line for line in fp)
    fp.close()

    cal = Calendar.from_ical(icalStr)

    datesAndSummaries = []
    summarySet = set()
    
    for c in cal.walk('VEVENT'):
        dateEnd = c.decoded('DTEND')
        summary = c.decoded('SUMMARY')
        rrule = c.get('RRULE')
        
        # TODO: Will only handle one timezone per calendar
        # If this is a recurring event, get all the occurences
        # Note that the end date is used to construct the recurrence since this is when the file finishes recording
        if rrule != None:
            origTz = None if dateEnd.tzinfo == None else pytz.timezone(str(dateEnd.tzinfo))
            dateEnd = dateEnd.replace(tzinfo=None)
            for d in list(rrulestr(rrule.to_ical(), forceset=True, dtstart=dateEnd)):
                if origTz != None:
                    # Need to be careful with the timezones here because rrule will interpret all the expanded entries to be in the same timezone/DST setting as the first, so to make sure all dates are converted to UTC correctly remove the timezone and then localize each time before conversion
                    datesAndSummaries.append( (origTz.localize(d).astimezone(pytz.utc), summary) )
                else:
                    datesAndSummaries.append( (d, summary) )
        else:
            if origTz != None:
                datesAndSummaries.append( (dateEnd.astimezone(pytz.utc), summary) )
            else:
                datesAndSummaries.append( (dateEnd, summary) )

        summarySet.add(summary)

    # TODO: Returns a list of datesAndSummaries, O(n) to search through, would be better off with a binary tree structure or something else
    return (datesAndSummaries, origTz)

# Read files from directory and get mtimes in UTC
def get_files_mtimes(inputDir, origTz):
    filesAndMtimes = []
    for f in os.listdir(inputDir):
        f = os.path.join(inputDir, f)
        if os.path.isfile(f):
            if origTz == None:
                filesAndMtimes.append( (f, datetime.datetime.utcfromtimestamp(os.path.getmtime(f))) )
            else:
                filesAndMtimes.append( (f, origTz.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(f))).astimezone(pytz.utc)) )
    return filesAndMtimes

# Match times from files and calendar, copying them to the specified output directory
def match_files_cal(datesAndSummaries, filesAndTimes, maxDistMinsArg, inputDir, outputDir):
    
    # Copy the recording to the target directory with a new, formatted name
    def copyRecording(eventName, mtime, origName):
        targetName = str(eventName) + " " + mtime.strftime('%Y-%m-%d %H-%M') + origName[origName.rfind('.'):]
        targetPath = os.path.join(outputDir, targetName)

        sourcePath = os.path.join(inputDir, origName)

        shutil.copy2(sourcePath, targetPath)
   
    # Check if the user has manually set a maximum distance, if not use the default
    maxDistMins = maxDistMinsArg if maxDistMinsArg != None else defaultMaxDistMins
    delta = datetime.timedelta(minutes=maxDistMins)
    
    multiMatches = 0
    noMatches = 0
    matches = 0
    for f in filesAndTimes:
        # Get all calendar entries within the max dist of this file mtime
        close = [entry for entry in datesAndSummaries if abs(entry[0] - f[1]) <= delta] 

        if len(close) < 1:
            # No matches, copy as uncategorised
            logging.info("No matches for '" + str(f[0]) + "' (finished at " + str(f[1]) + ")")
            copyRecording('Unknown', f[1], str(f[0]))         
            noMatches += 1
        elif len(close) == 1:
            # Exactly one match, add to the list of matches
            logging.debug("Matched " + str(f[0]) + " (finished at " + str(f[1]) + ") to '" + close[0][1] + "' (finished at " + str(close[0][0]) + "). Distance " + str(int(abs(close[0][0] - f[1]).total_seconds()/60)) + " minutes.")
            copyRecording(close[0][1], f[1], str(f[0]))
            matches += 1
        else:
            # Multi matches, set as uncategorised
            logging.info("Multiple matches for '" + str(f[0]) + "' (finished at " + str(f[1]) + ")")
            copyRecording('Unknown', f[1], str(f[0]))         
            multiMatches += 1
    total = matches + noMatches + multiMatches
    print "Matched: %d (%d%%), Unmatched: %d (%d%%), Ambiguous: %d (%d%%) (Total: %d)" % (matches, (float(matches)/total)*100, noMatches, (float(noMatches)/total)*100, (float(multiMatches)/total)*100, multiMatches, total)
    
# Set up the argument parser and retrieve the command line parameters
def parse_arguments():
    parser = argparse.ArgumentParser(description='Organise recordings by linking them to calendar events from an ical source.')
    parser.add_argument('icalFile', metavar='icalFile', type=str, help='The filename of the ical file to be parsed.')
    parser.add_argument('inputDir', metavar='inputDir', type=str, help='The input directory, all files in this directory will have their modified times checked.')
    parser.add_argument('outputDir', metavar='outputDir', type=str, help='The output directory, the files will be copied to here with their new names.')
    parser.add_argument('--maxDistMins', metavar='maxDistMins', type=int, help='The maximum distance in minutes allowed from a recording time to a corresponding event time for it to be considered a match. (default: ' + str(defaultMaxDistMins) + ')')
    return parser.parse_args()

if __name__ == "__main__":
    defaultMaxDistMins = 90

    # Set up logging
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    args = parse_arguments()

    print "Getting calendar from " + args.icalFile
    datesAndSummaries, origTz = get_calendar_tuples(args.icalFile)
    if len(datesAndSummaries) < 1:
        logging.warning("No entries retrieved from calendar, all files will be uncategorised") 

    filesAndTimes = get_files_mtimes(args.inputDir, origTz)

    match_files_cal(datesAndSummaries, filesAndTimes, args.maxDistMins, args.inputDir, args.outputDir)
    print "Finished"
