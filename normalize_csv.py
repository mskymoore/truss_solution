import argparse, logging, sys
import unicodedata, datetime


# instantiate cli argument parser
parser = argparse.ArgumentParser()

# configure cli argument parser
parser.add_argument('-v', '--verbose', action='count',
                    help='Increases verbosity of output by one level for each v flag, up to 3.')
parser.add_argument('-l', '--logToFile', action='store_true',
                    help='Logs to a file if included, verbosity affected by v flag.')

# parse arguments
args = parser.parse_args()


# default log level
logLevel = logging.WARNING

# handle verbosity log level change
if args.verbose:
    # v arguments will be counted when parsed, 
    # ie if '-vv' is passed then args.verbose == 2
    if args.verbose == 1:
        logLevel = logging.WARNING
    elif args.verbose == 2:
        logLevel = logging.INFO
    elif args.verbose >= 3:
        logLevel = logging.DEBUG

# instantiate logging
log = logging.getLogger(__name__)

# configure logging
logFormatter = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
log.setLevel(logLevel)

# handle logging to file
if args.logToFile:
    # instantiate file handler
    fileHandler = logging.FileHandler('normalizeCSV.log')
    # configure file handler
    fileHandler.setFormatter(logFormatter)
    # add file handler to logging utility
    log.addHandler(fileHandler)

# handle logging to console
# instantiate stream handler
streamHandler = logging.StreamHandler()
# configure stream handler
streamHandler.setFormatter(logFormatter)
# add stream handler to logging utility
log.addHandler(streamHandler)


# takes a list of number strings that are max 2 digits long
# pads 1 digit strings with a zero in front
def padNumsWithZero(listNumStrings):
    for i, num in enumerate(listNumStrings):
        if len(num) == 1:
            listNumStrings[i] = '0' + num


# takes a duration string in the form HH:MM:SS.MS
# returns floating point representation in seconds
def convertDurationToSeconds(durationString):
    seconds = 0.0
    hrs, mins, secs = durationString.split(':')
    secs, milsecs = secs.split('.')
    seconds += int(hrs)*3600 + int(mins)*60 + int(secs) + (float(milsecs)/1000)
    return seconds


# takes a string and returns a boolean indicating
# if the string contains the unicode replacement character
def strHasReplacementCharacter(aString):
    if aString.count('\xEF') > 0:
        return True
    return False



def main():

    # read input
    _input = sys.stdin.readlines()

    # sting variable for output csv
    # assuming no utf-8 encoding errors in header line
    output = _input[0]

    log.info('beginning reading input from stdin')
    # read lines one at a time from stdin
    for line in _input[1:]:
        normalizedLine = str()
        log.info('read line : ' + line)
        
        # decode the line
        line = line.decode(encoding='utf-8', errors='replace')
        
        # normalize the characters
        line = unicodedata.normalize('NFKC', line).encode('utf-8')
        log.debug('normalized line : ' + line)
        
        ## convert timestamp to ISO-8601
        log.debug('BEGIN TIMESTAMP CONVERSION')
        
        # get timestamp string
        timestamp, comma, remainder = line.partition(',')
        log.debug('original timestamp was ' + timestamp)

        # make sure timestamp is parseable
        if strHasReplacementCharacter(timestamp):
            log.warning('replacement character in timestamp dropping \
                         the following line from output:\n' + line)
            continue

        # break into component parts
        timestampParts = timestamp.split(' ')
        
        # normalize and pad with zeros for iso conversion
        dateParts = timestampParts[0].split('/')
        timeParts = timestampParts[1].split(':')
        padNumsWithZero(dateParts)
        padNumsWithZero(timeParts)
        
        # recreate timestamp string
        timestamp = ' '.join(['/'.join(dateParts), ':'.join(timeParts), timestampParts[2]])
        log.debug('padded timestamp is ' + timestamp)
        
        # create datetime object from timestamp string
        timestamp = datetime.datetime.strptime(timestamp, '%m/%d/%y %I:%M:%S %p')
        log.debug('pacific time was ' + timestamp.isoformat())
        
        # convert to pacific timezone
        timestamp += datetime.timedelta(hours=3)
        log.debug('eastern time is ' + timestamp.isoformat())

        # put timestamp on normalized line
        normalizedLine += timestamp.isoformat() + ','
        log.debug('normalizedLine = ' + normalizedLine)
        log.debug('remainder = ' + remainder)

        ## get address
        log.debug('BEGIN ADDRESS ACQUISITION')

        # assuming quotations are paired, correct, and don't contain other quotations
        address, comma, remainder = remainder.partition(',')
        if address.count('"') > 0 or address.count("'") > 0:
            if address.count('"') > 0:
                addressRemainder, endQuote, remainder = remainder.partition('"')
            elif address.count("'") > 0:
                addressRemainder, endQuote, remainder = remainder.partition("'")
            address += addressRemainder + endQuote
            remainder = remainder[1:]
        log.debug('address component is ' + address)
        
        # put address on normalized line
        normalizedLine += address + ','
        log.debug('normalizedLine = ' + normalizedLine)
        log.debug('remainder = ' + remainder)

        ## make zip code 5 digits, pad with zeros in front if less than 5 digits
        log.debug('BEGIN ZIP CODE NORMALIZATION')

        # get zip code
        zipcode, comma, remainder = remainder.partition(',')
        log.debug('original zipcode was ' + zipcode)

        # normalize zip code
        zipcodeLength = len(zipcode)
        if zipcodeLength < 5:
            neededZeros = 5 - zipcodeLength
            zipcode = '0'*neededZeros + zipcode
            log.debug('normalized zipcode is ' + zipcode)
        elif zipcodeLength > 5:
            # take last five digits, and discard leading digits
            zipcode = zipcode[-5:]
            log.debug('normalized zipcode is ' + zipcode)
        
        # put zip code on normalized line
        normalizedLine += zipcode + ','
        log.debug('normalizedLine = ' + normalizedLine)
        log.debug('remainder = ' + remainder)

        ## convert name columns to upper case
        log.debug('BEGIN NAME NORMALIZATION')

        # get name
        name, comma, remainder = remainder.partition(',')
        log.debug('original name was ' + name)

        # normalize name
        if not name.isupper():
            name = name.upper()
            log.debug('normalized name is ' + name)

        # put normalized name on normalized line
        normalizedLine += name + ','
        log.debug('normalizedLine = ' + normalizedLine)
        log.debug('remainder = ' + remainder)

        ## Convert FooDuration and BarDuration from HH:MM:SS.MS to floating point seconds format
        log.debug('BEGIN DURATIONS CONVERSION')

        # get fooDuration
        fooDuration, comma, remainder = remainder.partition(',')
        log.debug('original fooDuration was ' + fooDuration)

        # make sure fooDuration is parseable
        if strHasReplacementCharacter(fooDuration):
            log.warning('fooDuration has replacement character and won\'t \
                         convert properly, dropping the following line from \
                         output:\n' + line)
            continue

        # normalize fooDuration
        fooDuration = convertDurationToSeconds(fooDuration)
        log.debug('floating point fooDuration is ' + str(fooDuration))

        # put normalized fooDuration on normalized line
        normalizedLine += str(fooDuration) + ','
        log.debug('normalizedLine = ' + normalizedLine)
        log.debug('remainder = ' + remainder)

        # get barDuration
        barDuration, comma, remainder = remainder.partition(',')
        log.debug('original barDuration was ' + barDuration)

        # make sure barDuration is parseable
        if strHasReplacementCharacter(barDuration):
            log.warning('barDuration has replacement character and won\'t \
                         convert properly, dropping the following line from \
                         output:\n' + line)
            continue

        # normalize barDuration
        barDuration = convertDurationToSeconds(barDuration)
        log.debug('floating point barDuration is ' + str(barDuration))

        # put normalized barDuration on normalized line
        normalizedLine += str(barDuration) + ','
        log.debug('normalizedLine = ' + normalizedLine)
        log.debug('remainder = ' + remainder)

        ## make TotalDuration the sum of fooDuration and barDuration
        log.debug('BEGIN TOTALDURATION REPLACEMENT')
        
        # get totalDuration
        totalDuration, comma, remainder = remainder.partition(',')
        log.debug('original totalDuration was ' + totalDuration)
        
        # make new totalDuration
        totalDuration = fooDuration + barDuration
        log.debug('normalized totalDuration is ' + str(totalDuration))
        
        # put totalDuration on normalized line
        normalizedLine += str(totalDuration) + ','
        log.debug('normalizedLine = ' + normalizedLine)
        log.debug('remainder = ' + remainder)
        
        # put the notes column on normalized line
        normalizedLine += remainder

        # append the normalized line to the output
        log.info('processed line : ' + normalizedLine)
        output += normalizedLine
    
    # write the output
    log.info('writing output to stdout')
    sys.stdout.writelines(output)


if __name__ == '__main__':
    main()