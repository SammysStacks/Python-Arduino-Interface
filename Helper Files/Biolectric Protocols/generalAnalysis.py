

# -------------------------------------------------------------------------- #
# ---------------------------- Imported Modules ---------------------------- #

# Basic Modules
import scipy
import numpy as np
# Filtering Modules
from scipy.signal import savgol_filter
# Matlab Plotting Modules
import matplotlib.pyplot as plt
# Feature Extraction Modules
from scipy.stats import skew
from scipy.stats import entropy
from scipy.stats import kurtosis

# Import Files
import _filteringProtocols as filteringMethods # Import Files with Filtering Methods
        
# ---------------------------------------------------------------------------#
# ---------------------------------------------------------------------------#

class analysisProtocol:
    
    def __init__(self, numPointsPerBatch = 3000, moveDataFinger = 10, numChannels = 2, plottingClass = None):
        # Input Parameters
        self.numChannels = numChannels            # Number of Bioelectric Signals
        self.numPointsPerBatch = numPointsPerBatch        # The X-Wdith of the Plot (Number of Data-Points Shown)
        self.moveDataFinger = moveDataFinger      # The Amount of Data to Stream in Before Finding Peaks
        self.plotStreamedData = plottingClass != None  # Plot the Data
        self.plottingClass = plottingClass
                
        # Define the class with all the filtering methods
        self.filteringMethods = filteringMethods.filteringMethods()
        # High Pass Filter Parameters
        self.dataPointBuffer = 5000        # A Prepended Buffer in the Filtered Data that Represents BAD Filtering; Units: Points
        self.cutOffFreq = [.01, 50]        # Optimal LPF Cutoff in Literatrue is 6-8 or 20 Hz (Max 35 or 50); I Found 25 Hz was the Best, but can go to 15 if noisy (small amplitude cutoff)
                
        # Prepare the Program to Begin Data Analysis
        self.checkParams()              # Check to See if the User's Input Parameters Make Sense
        self.resetGlobalVariables()     # Start with Fresh Inputs (Clear All Arrays/Values)
                
        # If Plotting, Define Class for Plotting Peaks
        if self.plotStreamedData and numChannels != 0:
            self.initPlotPeaks()
        
    def resetGlobalVariables(self):
        # Data to Read in
        self.data = [ [], [[] for channel in range(self.numChannels)] ]
        
        # General parameters
        self.samplingFreq = None        # The Average Number of Points Steamed Into the Arduino Per Second; Depends on the User's Hardware; If NONE Given, Algorithm will Calculate Based on Initial Data

        # Close Any Opened Plots
        if self.plotStreamedData:
            plt.close()
            
    def checkParams(self):
        assert self.moveDataFinger < self.numPointsPerBatch, "You are Analyzing Too Much Data in a Batch. 'moveDataFinger' MUST be Less than 'numPointsPerBatch'"
        
    def setSamplingFrequency(self, startBPFindex):
        # Caluclate the Sampling Frequency
        self.samplingFreq = len(self.data[0][startBPFindex:])/(self.data[0][-1] - self.data[0][startBPFindex])
        print("\n\tSetting Temperature Sampling Frequency to", self.samplingFreq)
        print("\tFor Your Reference, If Data Analysis is Longer Than", self.moveDataFinger/self.samplingFreq, ", Then You Will NOT be Analyzing in Real Time")
        
    def initPlotPeaks(self): 
        # Establish pointers to the figure
        self.fig = self.plottingClass.fig
        axes = self.plottingClass.axes

        # Plot the Raw Data
        yLimLow = 0; yLimHigh = 3.3; 
        self.bioelectricDataPlots = []; self.bioelectricPlotAxes = []
        for channelIndex in range(self.numChannels):
            # Create Plots
            if self.numChannels == 1:
                self.bioelectricPlotAxes.append(axes[0])
            else:
                self.bioelectricPlotAxes.append(axes[channelIndex, 0])
            
            # Generate Plot
            self.bioelectricDataPlots.append(self.bioelectricPlotAxes[channelIndex].plot([], [], '-', c="tab:red", linewidth=1, alpha = 0.65)[0])
            
            # Set Figure Limits
            self.bioelectricPlotAxes[channelIndex].set_ylim(yLimLow, yLimHigh)
            # Label Axis + Add Title
            self.bioelectricPlotAxes[channelIndex].set_ylabel("Incoming Data", fontsize=13, labelpad = 10)
            
        # Create the Data Plots
        self.filteredBioelectricDataPlots = []
        self.filteredBioelectricPlotAxes = [] 
        for channelIndex in range(self.numChannels):
            # Create Plot Axes
            if self.numChannels == 1:
                self.filteredBioelectricPlotAxes.append(axes[1])
            else:
                self.filteredBioelectricPlotAxes.append(axes[channelIndex, 1])
            
            # Plot Flitered Peaks
            self.filteredBioelectricDataPlots.append(self.filteredBioelectricPlotAxes[channelIndex].plot([], [], '-', c="tab:red", linewidth=1, alpha = 0.65)[0])

            # Set Figure Limits
            self.filteredBioelectricPlotAxes[channelIndex].set_ylim(yLimLow, yLimHigh)
            
        # Tighten figure's white space (must be at the end)
        self.plottingClass.fig.tight_layout(pad=2.0);
        
    # ----------------------------------------------------------------------- #
    # ------------------------- Data Analysis Begins ------------------------ #

    def analyzeData(self, dataFinger, predictionModel = None, actionControl = None):
        
        # Add incoming Data to Each Respective Channel's Plot
        for channelIndex in range(self.numChannels):
            
            # ---------------------- Filter the Data ----------------------- #    
            # Band Pass Filter to Remove Noise
            startBPFindex = max(dataFinger - self.dataPointBuffer, 0)
            yDataBuffer = self.data[1][channelIndex][startBPFindex:dataFinger + self.numPointsPerBatch].copy()
            endDataPointer = startBPFindex + len(yDataBuffer) - 1
            
            # Get the Sampling Frequency from the First Batch (If Not Given)
            if not self.samplingFreq:
                self.setSamplingFrequency(startBPFindex)

            # Filter the Data: Low pass Filter and Savgol Filter
            filteredData = self.filteringMethods.bandPassFilter.butterFilter(yDataBuffer, self.cutOffFreq[1], self.samplingFreq, order = 3, filterType = 'low')
            filteredData = savgol_filter(filteredData, 21, 2, mode='nearest', deriv=0)[-(endDataPointer - dataFinger + 1):]
            # Format data and timepoints
            timePoints = np.array(self.data[0][-len(filteredData):])
            filteredData = np.array(filteredData)
            # --------------------------------------------------------------- #
                    
            # ------------------- Plot Biolectric Signals ------------------- #
            if self.plotStreamedData:
                # Get X Data: Shared Axis for All Channels
                timePoints = np.array(self.data[0][dataFinger:dataFinger + self.numPointsPerBatch])
    
                # Get New Y Data
                newYData = self.data[1][channelIndex][dataFinger:dataFinger + self.numPointsPerBatch]
                # Plot Raw Bioelectric Data (Slide Window as Points Stream in)
                self.bioelectricDataPlots[channelIndex].set_data(timePoints, newYData)
                self.bioelectricPlotAxes[channelIndex].set_xlim(timePoints[0], timePoints[-1])
                            
                # Plot the Filtered + Digitized Data
                self.filteredBioelectricDataPlots[channelIndex].set_data(timePoints, filteredData[-len(timePoints):])
                self.filteredBioelectricPlotAxes[channelIndex].set_xlim(timePoints[0], timePoints[-1]) 
            # --------------------------------------------------------------- #   
    
    
    
    
    