# make sure only copying measurement values, not extraneous info

"""
 lidar sensor outputs uncompressed data files named raw_data_XYZ.log where XYZ is a natural number with up to three digits.
 These files are originally stored in /raw_data.
 
 this program compresses these raw data files into a small number of hdf5 files in ascending order
 
 Lidar Files
    --> raw_data
        --> raw_data_XYZ.log
    
    --> compressed_data
        YYYYMMDDHHMMSS.h5
    
    --> data_compressor.py
    
    --> data_compressor_error_log.log
        

"""

import os
from time import sleep
from datetime import datetime
import numpy as np
import h5py

INPUT_DIR = "raw_data"
OUTPUT_DIR = "compressed_data"
LOG_FILE_NAME = "data_compressor_error_log.log"
MIN_TO_SLEEP = 10;  # time to let files complete writing before processing, 3x lidar output interval suggested
BASE_OF_DATA_POINTS = 16 # should be in hexadecimal
ERRORS_ONLY = False

log_file = open(LOG_FILE_NAME, "a+")  # opens the log file (or creates it if it does not exist)
incorrectly_formatted_files = [] # so warnings don't flood error log
if not os.path.exists(OUTPUT_DIR): # make OUTPUT_DIR if it doesn't exist
    os.makedirs(OUTPUT_DIR)


def main():
    
    while(True):
        # get all files in directory
        files_in_dir = os.listdir(INPUT_DIR) 
        
        # sleeps for MIN_TO_SLEEP, let files_in_dir finish writing
        sleep(60 * MIN_TO_SLEEP);
        
        files_to_compress = get_files_to_compress(files_in_dir)
        
        if(len(files_to_compress) == 0):
            continue
        
        files_to_compress.sort() # ensures that data is in correct order
        
        compressed_data_file_name = get_name(files_to_compress[0])
        compressed_data = [] # data for the entire loop of files
        files_to_delete =[]
        
        try: # to initialize compressed_data_file
            compressed_data_file = h5py.File(os.path.join(OUTPUT_DIR, compressed_data_file_name + ".h5"), 'w')
        except:
            log_error("could not create compressed data file: " + compressed_data_file_name)
            raise Exception("well shit")
        
        
        
        
        for file in files_to_compress: # loop through all files to compress
            
            try: # to open file
                input_file = open(os.path.join(INPUT_DIR, file), "r")
            except:
                log_error("could not open input file: " + input_file.name)
                continue  # skip loop iteration so file is not deleted
            
            line = input_file.readline()
            
            # loop through input file, compress each line, and write to output file
            while(line != ""):
                try: # to compress line
                    compressed_line = parse_line(line)
                    compressed_data.append(compressed_line)
                except Exception as e:
                    log_warning("could not parse line in file: " + input_file.name + ": " + line)
                
                line = input_file.readline()
                    
            input_file.close()
            files_to_delete.append(file)
            print("processing file " + file)
            
            
        
        try: # to write compressed data to compressed_data_file
            assert(len(compressed_data) > 0)
            array_of_data = np.array([np.array(line) for line in compressed_data]) # convert list of lists to 2D numpy array
            compressed_data_file.create_dataset("data", data=array_of_data) # TODO get data to be of same length
        except Exception as e:
            log_error("could not create dataset: in " + compressed_data_file_name)
            raise e
    
    
        for file in files_to_delete:
            try: # to delete used raw data files
                os.remove(os.path.join(INPUT_DIR, file))
            except Exception as e:
                #print(repr(e))
                log_warning("could not delete raw data file: " + file)
                              
                              
        compressed_data_file.close() # writes compressed_data_file to the disk
        
        
def get_name(file):
    f = open(os.path.join(INPUT_DIR, file), "r")
    
    return f.readline()[:23].replace(":","").replace(".","").replace("-","").replace(" ","")
    
          
def is_raw_data(f):
    """ returns true if file name is of correct format, returns false otherwise """
    
    name = os.path.basename(f)
    split_name = name.split(".")  # {filename, extension}
    
    # checks that f is a log file that starts with "raw_data"
    if(split_name[1] == "log" and split_name[0][0:8] == "raw_data"):
        if(len(split_name[0]) == 8): # if file is "raw_data.log"
            return True
        elif(split_name[0][0:9] == "raw_data_"): # if the file name starts with "raw_data_"
            try:  # tries to parse the number of the file as an int
                file_num = int(split_name[0][9:])
                return True
            except:
                pass

    if(f not in incorrectly_formatted_files):
        incorrectly_formatted_files.append(f)
        log_warning("raw_data file name may be incorrectly formatted: " + name)
        
    return False

def get_files_to_compress(file_list):
    output =[]
    
    for file in file_list:
        if(is_raw_data(file)):
            output.append(file)
    
    return output

def parse_line(l):
    """ returns a list of data from line l in a raw_data file. If line cannot be compressed, raises exception """
    
    # transmission type is sSN LMDscandata CoLa A Hex
    # telegram is hex --> convert to ascii --> convert to hex
    
    
    index = l.index("<") # get first < in line
    line = l[index:].replace('<',"").replace(">","")
    
    
    # convert line from hex to ascii
    ascii_line = bytes.fromhex(line).decode('ASCII')
    #print(ascii_line)
    
    # get transmission parts
    transmission_parts = ascii_line.split(" ")
    
    assert (len(transmission_parts) == 413), "line has incorrect data: " + l
    
    num_data_points = int(transmission_parts[25], BASE_OF_DATA_POINTS)
    assert(len(transmission_parts)- 26 - 6 == num_data_points)
    
    # converts data_point in string with specified base to decimal int
    return [int(point, BASE_OF_DATA_POINTS) for point in transmission_parts[26:-6]]

def log_error(error_string):
    """ write string s to log file and screen """
    error = "[ERROR] " + str(datetime.now()) + " " + error_string
    log_file.write(error + "\n")
    log_file.flush() # remove this for increased performance
    print(error)

def log_warning(warning_string):
    """ write string s to log file and screen """
    warning = "[WARNING] " + str(datetime.now()) + " " + warning_string
    log_file.write(warning + "\n")
    log_file.flush() # remove this for increased performance
    if(not ERRORS_ONLY):
        print(warning)

if(__name__ == "__main__"):  # just a workaround to call functions before they are defined
    main()
