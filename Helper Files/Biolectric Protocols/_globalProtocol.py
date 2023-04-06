
# -------------------------------------------------------------------------- #
# ---------------------------- Imported Modules ---------------------------- #

# Abstract class
import abc
# Plotting
import matplotlib.pyplot as plt

# Import Files
import _filteringProtocols # Import files with filtering methods
import _universalProtocols # Import files with general analysis methods

# -------------------------------------------------------------------------- #
# --------------------------- Global Model Class --------------------------- #

class globalProtocol(abc.ABC):
    
    def __init__(self, numPointsPerBatch = 3000, moveDataFinger = 10, numChannels = 2, plottingClass = None, readData = None):
        # General input parameters
        self.plotStreamedData = plottingClass != None       # Plot the Data
        self.numPointsPerBatch = numPointsPerBatch          # The X-Wdith of the Plot (Number of Data-Points Shown)
        self.moveDataFinger = moveDataFinger                # The Amount of Data to Stream in Before Finding Peaks
        self.plottingClass = plottingClass
        self.featureAverageWindow = None    # The number of seconds before each feature to avaerage the features together. Set in streamData if collecting features.
        self.numChannels = numChannels      # Number of Bioelectric Signals
        self.collectFeatures = False        # This flag will be changed by user if desired (NOT here).
        self.readData = readData
        
        # Prepare the Program to Begin Data Analysis
        self.checkAllParams()               # Check to See if the User's Input Parameters Make Sense
        self.resetGlobalVariables()         # Start with Fresh Inputs (Clear All Arrays/Values)
        
        # Define general classes to process data.
        self.filteringMethods = _filteringProtocols.filteringMethods()
        self.universalMethods = _universalProtocols.universalMethods()
        
        # If Plotting, Define Class for Plotting Peaks
        if self.plotStreamedData and numChannels != 0:
            self.initPlotPeaks()
            
    def resetGlobalVariables(self):
        # Data to Read in
        self.data = [ [], [[] for channel in range(self.numChannels)] ]
        # Reset Feature Extraction
        self.rawFeatures = []           # Raw features extraction at the current timepoint.
        self.featureTimes = []          # The time of each feature.
        self.compiledFeatures = []      # FINAL compiled features at the current timepoint. Could be average of last x features.
        
        # General parameters
        self.samplingFreq = None            # The Average Number of Points Steamed Into the Arduino Per Second; Depends on the User's Hardware; If NONE Given, Algorithm will Calculate Based on Initial Data
        self.lastAnalyzedDataInd = 0        # The index of the last point analyzed  

        # Close Any Opened Plots
        if self.plotStreamedData:
            plt.close('all')
            
        self.resetAnalysisVariables()
    
    def checkAllParams(self):
        assert self.moveDataFinger < self.numPointsPerBatch, "You are Analyzing Too Much Data in a Batch. 'moveDataFinger' MUST be Less than 'numPointsPerBatch'"
        self.checkParams()

    def setSamplingFrequency(self, startFilterPointer):
        # Caluclate the Sampling Frequency
        self.samplingFreq = len(self.data[0][startFilterPointer:])/(self.data[0][-1] - self.data[0][startFilterPointer])
        print("\n\tSetting Sampling Frequency to", self.samplingFreq)
        print("\tFor Your Reference, If Data Analysis is Longer Than", self.moveDataFinger/self.samplingFreq, ", Then You Will NOT be Analyzing in Real Time")
        
        self.setSamplingFrequencyParams()  
        
    # ------------------------ Child Class Contract ------------------------ #
    
    @abc.abstractmethod
    def resetAnalysisVariables(self):
        """ Create contract for child class method """
        raise NotImplementedError("Must override in child")  
        
    @abc.abstractmethod
    def checkParams(self):
        """ Create contract for child class method """
        raise NotImplementedError("Must override in child")        

    @abc.abstractmethod
    def setSamplingFrequencyParams(self):
        """ Create contract for child class method """
        raise NotImplementedError("Must override in child")  

    @abc.abstractmethod
    def initPlotPeaks(self):
        """ Create contract for child class method """
        raise NotImplementedError("Must override in child")  
        
    @abc.abstractmethod
    def analyzeData(self):
        """ Create contract for child class method """
        raise NotImplementedError("Must override in child") 
        
    @abc.abstractmethod
    def filterData(self):
        """ Create contract for child class method """
        raise NotImplementedError("Must override in child") 
        
    # ---------------------------------------------------------------------- #


    
# -------------------------------------------------------------------------- #
