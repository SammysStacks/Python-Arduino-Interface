#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  2 13:44:26 2021

@author: samuelsolomon
"""

# -------------------------------------------------------------------------- #
# ---------------------------- Imported Modules ---------------------------- #

# General modules
import sys
import math
import numpy as np
from datetime import datetime
# Plotting
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator # added 

# Folder with Data Aquisition Files
sys.path.append('Helper Files/Biolectric Protocols/')
sys.path.append('Biolectric Protocols/')
# Import Bioelectric Analysis Files
from emgAnalysis import emgProtocol
from eogAnalysis import eogProtocol
from eegAnalysis import eegProtocol
from gsrAnalysis import gsrProtocol
from generalAnalysis import generalProtocol
from temperatureAnalysis import tempProtocol

# Import Modules to Read in Data
import arduinoInterface as arduinoInterface      # Functions to Read in Data from Arduino

class plotDataTopLevel():
    
    def __init__(self, numChannels, channelDist, analysisOrder):
        matplotlib.use('Qt5Agg') # Set Plotting GUI Backend   
        # use ggplot style for more sophisticated visuals
        plt.style.use('seaborn-poster')
        
        # Specify Figure aesthetics
        figWidth = 20; figHeight = 15;
        self.fig, axes = plt.subplots(numChannels, 2, sharey=False, sharex = False, gridspec_kw={'hspace': 0},
                                     figsize=(figWidth, figHeight))
        if numChannels == 1:
            axes = np.array([axes])
            
        self.axes = {}
        # Distribute the axes to their respective sensor
        for biomarkerInd in range(len(analysisOrder)):
            biomarkerType = analysisOrder[biomarkerInd]
            streamingChannels = channelDist[biomarkerInd]
            self.axes[biomarkerType] = axes[streamingChannels]
                    
        # # Add experiment information to the plot
        # self.experimentText = "Current experiment: General data collection"
        
        # Create surrounding figure
        self.fig.add_subplot(111, frame_on=False)
        plt.tick_params(labelcolor="none", bottom=False, left=False)
        # Add figure labels
        plt.suptitle('Streaming Biolectric Data for Stress Prediction', fontsize = 22, x = 0.525, fontweight = "bold")
        plt.xlabel("Time (Seconds)", labelpad = 15)
        # Add axis column labels
        colHeaders = ["Raw signals", "Filtered signals"]
        for ax, colHeader in zip(axes[0], colHeaders):
            ax.set_title(colHeader, fontsize=17, pad = 15)
        
        # Remove overlap in yTicks
        nbins = len(axes[0][0].get_yticklabels())
        for axRow in axes:
            for ax in axRow:
                ax.yaxis.set_major_locator(MaxNLocator(nbins=nbins, prune='both'))  

        # Finalize figure spacing
        plt.tight_layout()
    
    def displayData(self):
        self.fig.show(); 
        self.fig.canvas.flush_events()
        self.fig.canvas.draw()

# -------------------------------------------------------------------------- #
# ---------------------------- Global Function ----------------------------- #

class streamingFunctions():
    
    def __init__(self, mainSerialNum, therapySerialNum, actionControl, numPointsPerBatch, moveDataFinger, streamingOrder, biomarkerOrder, plotStreamedData):

        # Store the arduinoRead Instance
        if mainSerialNum != None:
            self.arduinoRead = arduinoInterface.arduinoRead(mainSerialNum = mainSerialNum)
            self.mainArduino = self.arduinoRead.mainArduino
        
        # Variables that specify order of signals.
        self.biomarkerOrder = biomarkerOrder            # The order the features from each analysis are spliced together.
        self.streamingOrder = [streamingType.lower() for streamingType in streamingOrder] # The order the sensors are streamed in. Ex: ['eog', 'eog', 'eeg', 'gsr']
        self.analysisOrder = list(dict.fromkeys(streamingOrder)) # The order that the biomarkers will be analyzed
        # Store General Streaming Parameters.
        self.moveDataFinger = moveDataFinger        # The Minimum Number of NEW Data Points to Plot/Analyze in Each Batch;
        self.numPointsPerBatch = numPointsPerBatch  # The Number of Data Points to Display to the User at a Time;
        self.plotStreamedData = plotStreamedData    # Graph the Data to Show Incoming Signals + Analysis
        self.numChannels = len(self.streamingOrder) # The number of signals being streamed in.
        self.storeIncomingData = True

        # Variables that rely on the sensor data's order
        self.numChannelDist = [0 for _ in range(len(self.analysisOrder))] # Track the number of channels used by each sensor
        self.channelDist = [[] for _ in range(len(self.analysisOrder))]   # Track the order (its index) each sensor comes in
        # Populate the variables, accounting for the order.
        for analysisInd in range(len(self.analysisOrder)):
            biomarkerType = self.analysisOrder[analysisInd]
            # Organize the streaming channels by their respective biomarker.
            self.numChannelDist[analysisInd] = self.streamingOrder.count(biomarkerType)
            self.channelDist[analysisInd] = np.where(np.array(self.streamingOrder) == biomarkerType)[0]
        
            # Check That We Segmented the Channels Correctly
            assert self.numChannelDist[analysisInd] == len(self.channelDist[analysisInd]), "numChannelDist: " + str(self.numChannelDist) + "; channelDist: " + str(self.channelDist)
        # Check That We Segmented the Channels Correctly
        assert sum(self.numChannelDist) == self.numChannels, "The streaming map is missing values: " + str(self.streamingOrder)
        
        self.plottingClass = None;
        if self.plotStreamedData:
            self.plottingClass = plotDataTopLevel(self.numChannels, self.channelDist, self.analysisOrder)
        # Create Pointer to the Analysis Classes
        self.emgAnalysis = emgProtocol(self.numPointsPerBatch, self.moveDataFinger, self.numChannelDist[self.analysisOrder.index('emg')], self.plottingClass, self) if 'emg' in self.analysisOrder else None
        self.eogAnalysis = eogProtocol(self.numPointsPerBatch, self.moveDataFinger, self.numChannelDist[self.analysisOrder.index('eog')], self.plottingClass, self) if 'eog' in self.analysisOrder else None
        self.eegAnalysis = eegProtocol(self.numPointsPerBatch, self.moveDataFinger, self.numChannelDist[self.analysisOrder.index('eeg')], self.plottingClass, self) if 'eeg' in self.analysisOrder else None
        self.gsrAnalysis = gsrProtocol(self.numPointsPerBatch, self.moveDataFinger, self.numChannelDist[self.analysisOrder.index('gsr')], self.plottingClass, self) if 'gsr' in self.analysisOrder else None
        self.tempAnalysis = tempProtocol(self.numPointsPerBatch, self.moveDataFinger, self.numChannelDist[self.analysisOrder.index('temp')], self.plottingClass, self) if 'temp' in self.analysisOrder else None
        self.generalAnalysis = generalProtocol(self.numPointsPerBatch, self.moveDataFinger, self.numChannelDist[self.analysisOrder.index('general')], self.plottingClass, self) if 'general' in self.analysisOrder else None
        self.analysisProtocols = {
            'emg': self.emgAnalysis,
            'eog': self.eogAnalysis,
            'eeg': self.eegAnalysis,
            'gsr': self.gsrAnalysis,
            'temp': self.tempAnalysis,
            'general': self.generalAnalysis
        }
        
        self.analysisList  = [];
        # Generate a list of all analyses, keeping the order they are streamed in.
        for biomarkerType in self.analysisOrder:
            self.analysisList.append(self.analysisProtocols[biomarkerType]) 
        
        # Initialize mutable variables
        self.resetGlobalVariables()
    
    def resetGlobalVariables(self):
        # Reset the analysis information
        for analysis in self.analysisList:
            analysis.resetGlobalVariables()
        
    def setupArduinoStream(self, stopTimeStreaming, usingTimestamps = False):
        # self.arduinoRead.resetArduino(self.mainArduino, 10)
        # Read and throw out first few reads
        rawReadsList = []
        while (int(self.mainArduino.in_waiting) > 0 or len(rawReadsList) < 2000):
            rawReadsList.append(self.arduinoRead.readline(ser=self.mainArduino))
        
        if usingTimestamps:
            # Calculate the Stop Time
            timeBuffer = 0
            if type(stopTimeStreaming) in [float, int]:
                # Save Time Buffer
                timeBuffer = stopTimeStreaming
                # Get the Current Time as a TimeStamp
                currentTime = datetime.now().time()
                stopTimeStreaming = str(currentTime).replace(".",":")
            # Get the Final Time in Seconds (From 12:00am of the Current Day) to Stop Streaming
            stopTimeStreaming = self.convertToTime(stopTimeStreaming) + timeBuffer
        
        return stopTimeStreaming
    
    def recordData(self, maxVolt = 5, adcResolution = 1023):
        # Read in at least one point
        rawReadsList = []
        while (int(self.mainArduino.in_waiting) > 0 or len(rawReadsList) == 0):
            rawReadsList.append(self.arduinoRead.readline(ser=self.mainArduino))
            
        # Parse the Data
        Voltages, timePoints = self.arduinoRead.parseRead(rawReadsList, self.numChannels, maxVolt, adcResolution)
        # Organize the Data for Processing
        self.organizeData(timePoints, Voltages)
        
    def organizeData(self, timePoints, Voltages):
        if len(timePoints[0]) == 0:
            print("\t !!! NO POINTS FOUND !!!")
        
        # Update the data (if present) for each sensor
        for analysisInd in range(len(self.analysisList)):
            analysis = self.analysisList[analysisInd]

            analysis.data[0].extend(timePoints[0])            
            # Add the Data to the Correct Channel
            analysis.data[1][analysisInd].extend(Voltages[analysisInd])
            
    def convertToTime(self, timeStamp):
        if type(timeStamp) == str:
            timeStamp = timeStamp.split(":")
        timeStamp.reverse()
        
        currentTime = 0
        orderOfInput = [1E-6, 1, 60, 60*60, 60*60*24]
        for i, timeStampVal in enumerate(timeStamp):
            currentTime += orderOfInput[i]*int(timeStampVal)
        return currentTime
    
    def convertToTimeStamp(self, timeSeconds):
        hours = timeSeconds//3600
        remainingTime = timeSeconds%3600
        minutes = remainingTime//60
        remainingTime %=60
        seconds = math.floor(remainingTime)
        microSeconds = remainingTime - seconds
        microSeconds = np.round(microSeconds, 6)
        return hours, minutes, seconds, microSeconds

# -------------------------------------------------------------------------- #
# ---------------------------- Reading All Data ---------------------------- #

class mainArduinoRead(streamingFunctions):

    def __init__(self, mainSerialNum, actionControl, numPointsPerBatch, moveDataFinger, streamingOrder, biomarkerOrder, plotStreamedData):
        # Create Pointer to Common Functions
        super().__init__(mainSerialNum, None, actionControl, numPointsPerBatch, moveDataFinger, streamingOrder, biomarkerOrder, plotStreamedData)

    def analyzeBatchData(self, dataFinger, lastTimePoint, predictionModel, actionControl):
        # Analyze the current data
        for analysis in self.analysisList:
            analysis.analyzeData(dataFinger, predictionModel = predictionModel, actionControl = actionControl)

        # Plot the Data
        if self.plotStreamedData: self.plottingClass.displayData()
    
        # Move the dataFinger pointer to analyze the next batch of data
        return dataFinger + self.moveDataFinger
            
    def streamArduinoData(self, maxVolt, adcResolution, stopTimeStreaming, predictionModel = None, actionControl = None, numTrashReads=100, numPointsPerRead=300):
        """Stop Streaming When we Obtain `stopTimeStreaming` from Arduino"""
        print("Streaming in Data from the Arduino")
        # Reset Global Variable in Case it Was Previously Populated
        self.resetGlobalVariables()
        
        # Prepare the arduino to stream in data
        self.stopTimeStreaming = self.setupArduinoStream(stopTimeStreaming)
        timePoints = self.analysisList[0].data[0]
        dataFinger = 0
    
        try:
            # Loop Through and Read the Arduino Data in Real-Time
            while len(timePoints) == 0 or (timePoints[-1] - timePoints[0]) < self.stopTimeStreaming:
                # Stream in the Latest Data
                self.recordData(maxVolt, adcResolution)

                # When enough data has been collected, analyze the new data in batches.
                while len(timePoints) - dataFinger >= self.numPointsPerBatch:
                    dataFinger = self.analyzeBatchData(dataFinger, timePoints[-1], predictionModel, actionControl)
                
               # print(self.gsrAnalysis.data[1][0][-1])
                    
            # At the end, analyze all remaining data
            dataFinger = self.analyzeBatchData(dataFinger, timePoints[-1], predictionModel, actionControl)
                        
        except Exception as error:
            self.mainArduino.close();
            print(error)
                
        finally:
             # Close the Arduinos at the End
            print("\nFinished Streaming in Data; Closing Arduino\n")
            self.mainArduino.close();
        
    def streamExcelData(self, compiledRawData, experimentTimes, experimentNames, surveyAnswerTimes, 
                        surveyAnswersList, surveyQuestions, subjectInformationAnswers, subjectInformationQuestions, predictionModel = None, actionControl = None):
        print("\tAnalyzing the Excel Data")
        # Reset Global Variable in Case it Was Previously Populated
        self.resetGlobalVariables()

        # Extract the Time and Voltage Data
        timePoints, Voltages = compiledRawData; Voltages = np.array(Voltages)
        
        dataFinger = 0; generalDataFinger = 0;
        # Loop Through and Read the Excel Data in Pseudo-Real-Time
        while generalDataFinger < len(timePoints): 
            # Organize the Input Data
            self.organizeData([timePoints[generalDataFinger:generalDataFinger+self.moveDataFinger], []], Voltages[:,generalDataFinger:generalDataFinger+self.moveDataFinger])

            # When enough data has been collected, analyze the new data in batches.
            while generalDataFinger + self.moveDataFinger - dataFinger >= self.numPointsPerBatch:
                lastTimePoint = timePoints[min(generalDataFinger+self.moveDataFinger, len(timePoints)) - 1]
                dataFinger = self.analyzeBatchData(dataFinger, lastTimePoint, predictionModel, actionControl)
            
            # Move onto the next batch of data
            generalDataFinger += self.moveDataFinger
            
        # At the end, analyze all remaining data
        lastTimePoint = timePoints[min(generalDataFinger+self.moveDataFinger, len(timePoints)) - 1]
        dataFinger = self.analyzeBatchData(dataFinger, lastTimePoint, predictionModel, actionControl)

        # Finished Analyzing the Data
        print("\n\tFinished Analyzing Excel Data")




