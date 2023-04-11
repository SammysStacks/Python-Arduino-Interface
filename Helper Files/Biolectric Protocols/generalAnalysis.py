
# -------------------------------------------------------------------------- #
# ---------------------------- Imported Modules ---------------------------- #

# Basic Modules
import scipy
import numpy as np

# Import Files
import _globalProtocol

# ---------------------------------------------------------------------------#
# ---------------------------------------------------------------------------#

class generalProtocol(_globalProtocol.globalProtocol):
    
    def __init__(self, numPointsPerBatch = 3000, moveDataFinger = 10, numChannels = 2, plottingClass = None, readData = None):
        # Filter Parameters
        self.dataPointBuffer = 50000        # A Prepended Buffer in the Filtered Data that Represents BAD Filtering; Units: Points
        self.cutOffFreq = [0.05, 20]        # Low and high pass filter.
        # High-pass filter parameters.
        self.stopband_edge = 1           # Common values for EEG are 1 Hz and 2 Hz. If you need to remove more noise, you can choose a higher stopband edge frequency. If you need to preserve the signal more, you can choose a lower stopband edge frequency.
        self.passband_ripple = 0.1       # Common values for EEG are 0.1 dB and 0.5 dB. If you need to remove more noise, you can choose a lower passband ripple. If you need to preserve the signal more, you can choose a higher passband ripple.
        self.stopband_attenuation = 60   # Common values for EEG are 40 dB and 60 dB. If you need to remove more noise, you can choose a higher stopband attenuation. If you need to preserve the signal more, you can choose a lower stopband attenuation.
        
        # Initialize common model class
        super().__init__(numPointsPerBatch, moveDataFinger, numChannels, plottingClass, readData)

    def resetAnalysisVariables(self):
        pass
            
    def checkParams(self):
        pass
    
    def setSamplingFrequencyParams(self):
        pass

    def initPlotPeaks(self): 
        # Establish pointers to the figure
        self.fig = self.plottingClass.fig
        axes = self.plottingClass.axes['general'][0]

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
        yLimLow = -1.65; yLimHigh = 1.65; 
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
            
            # Get the Sampling Frequency from the First Batch (If Not Given)
            if not self.samplingFreq:
                self.setSamplingFrequency(startBPFindex)

            # Filter the Data: Low pass Filter and Savgol Filter
            _, filteredData, _ = self.filterData([], yDataBuffer)
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
    
    def filterData(self, timePoints, data):
        # Filter the Data: Low pass Filter and Savgol Filter
        filteredData = self.filteringMethods.bandPassFilter.butterFilter(data, self.cutOffFreq[1], self.samplingFreq, order = 3, filterType = 'low')
        filteredData = self.filteringMethods.bandPassFilter.high_pass_filter(filteredData, self.samplingFreq, self.cutOffFreq[0], self.stopband_edge, self.passband_ripple, self.stopband_attenuation)
        # filteredData = scipy.signal.savgol_filter(filteredData, 15, 2, mode='nearest', deriv=0)[-(endDataPointer - dataFinger + 1):]

        return [], filteredData, []
    
    
    