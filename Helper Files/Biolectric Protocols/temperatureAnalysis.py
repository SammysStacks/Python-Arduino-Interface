
# -------------------------------------------------------------------------- #
# ---------------------------- Imported Modules ---------------------------- #

# Basic Modules
import scipy
import numpy as np

# Import Files
import _globalProtocol
        
# ---------------------------------------------------------------------------#
# ---------------------------------------------------------------------------#

class tempProtocol(_globalProtocol.globalProtocol):
    
    def __init__(self, numPointsPerBatch = 2000, moveDataFinger = 200, numChannels = 1, plottingClass = None, readData = None):
        # Feature collection parameters
        self.featureTimeWindow = 60         # The duration of time that each feature considers; 5 - 15
        # High Pass Filter Parameters
        self.dataPointBuffer = 5000         # A Prepended Buffer in the Filtered Data that Represents BAD Filtering; Units: Points
        self.cutOffFreq = [None, 0.1]       # Optimal LPF Cutoff in Literatrue is 6-8 or 20 Hz (Max 35 or 50); I Found 25 Hz was the Best, but can go to 15 if noisy (small amplitude cutoff)
        
        # Initialize common model class
        super().__init__(numPointsPerBatch, moveDataFinger, numChannels, plottingClass, readData)
        
    def resetAnalysisVariables(self):
        # General parameters 
        self.startFeatureTimePointer = 0    # The start pointer of the feature window interval.
            
    def checkParams(self):
        assert self.featureTimeWindow < self.dataPointBuffer, "The buffer does not include enough points for the feature window"
        
    def setSamplingFrequencyParams(self):
        # Set Parameters
        self.lastAnalyzedDataInd = int(self.samplingFreq*self.featureTimeWindow)
        self.minPointsPerBatch = int(self.samplingFreq*self.featureTimeWindow/2)
        self.dataPointBuffer = max(self.dataPointBuffer, int(self.samplingFreq*15))

    def initPlotPeaks(self): 
        # Establish pointers to the figure
        self.fig = self.plottingClass.fig
        axes = self.plottingClass.axes['temp'][0]

        # Plot the Raw Data
        yLimLow = 20; yLimHigh = 45; 
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
            self.bioelectricPlotAxes[channelIndex].set_ylabel("Temperature (\u00B0C)", fontsize=13, labelpad = 10)
            
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

    def analyzeData(self, dataFinger):
        
        # Add incoming Data to Each Respective Channel's Plot
        for channelIndex in range(self.numChannels):
            
            # ---------------------- Filter the Data ----------------------- #    
            # Find the starting/ending points of the data to analyze
            startFilterPointer = max(dataFinger - self.dataPointBuffer, 0)
            dataBuffer = np.array(self.data[1][channelIndex][startFilterPointer:dataFinger + self.numPointsPerBatch])
            timePoints = np.array(self.data[0][startFilterPointer:dataFinger + self.numPointsPerBatch])
            
            # Get the Sampling Frequency from the First Batch (If Not Given)
            if not self.samplingFreq:
                self.setSamplingFrequency(startFilterPointer)
                
            # Filter the data and remove bad indices
            filteredTime, filteredData, goodIndicesMask = self.filterData(timePoints, dataBuffer)
            # --------------------------------------------------------------- #
            
            # ---------------------- Feature Extraction --------------------- #
            if self.collectFeatures:                
                # Extract features across the dataset
                while self.lastAnalyzedDataInd < len(self.data[0]):
                    featureTime = self.data[0][self.lastAnalyzedDataInd]
                    
                    # Find the start window pointer
                    self.startFeatureTimePointer = self.findStartFeatureWindow(self.startFeatureTimePointer, featureTime, self.featureTimeWindow)
                    # Compile the good data in the feature interval.
                    intervalTimes, intervalData = self.compileBatchData(filteredTime, filteredData, goodIndicesMask, startFilterPointer, self.startFeatureTimePointer)
                    
                    # Only extract features if enough information is provided.
                    if self.minPointsPerBatch < len(intervalTimes):
                        # Calculate and save the features in this window.
                        temperatureFeatures = self.extractFeatures(intervalTimes, intervalData)
                        self.readData.averageFeatures([featureTime], [temperatureFeatures], self.featureTimes, self.rawFeatures, self.compiledFeatures, self.featureAverageWindow)
                
                    # Keep track of which data has been analyzed 
                    self.lastAnalyzedDataInd += int(self.samplingFreq*1)
            # -------------------------------------------------------------- #  
        
            # ------------------- Plot Biolectric Signals ------------------- #
            if self.plotStreamedData:
                # Format the raw data:.
                timePoints = timePoints[dataFinger - startFilterPointer:] # Shared axis for all signals
                rawData = dataBuffer[dataFinger - startFilterPointer:]
                # Format the filtered data
                filterOffset = (goodIndicesMask[0:dataFinger - startFilterPointer]).sum(axis = 0, dtype=int)

                # Plot Raw Bioelectric Data (Slide Window as Points Stream in)
                self.bioelectricDataPlots[channelIndex].set_data(timePoints, rawData)
                self.bioelectricPlotAxes[channelIndex].set_xlim(timePoints[0], timePoints[-1])
                                            
                # Plot the Filtered + Digitized Data
                self.filteredBioelectricDataPlots[channelIndex].set_data(filteredTime[filterOffset:], filteredData[filterOffset:])
                self.filteredBioelectricPlotAxes[channelIndex].set_xlim(timePoints[0], timePoints[-1]) 
            # --------------------------------------------------------------- #   
    
    def filterData(self, timePoints, data):
        # Filter the data
        filteredData = self.filteringMethods.bandPassFilter.butterFilter(data, self.cutOffFreq[1], self.samplingFreq, order = 1, filterType = 'low')
        
        # Find the bad points associated with motion artifacts
        deriv = abs(np.gradient(filteredData, timePoints))
        motionIndices = deriv > 0.1
        motionIndices_Broadened = scipy.signal.savgol_filter(motionIndices, max(3, int(self.samplingFreq*20)), 1, mode='nearest', deriv=0)
        goodIndicesMask = motionIndices_Broadened < 0.01
        
        # Remove the bad points from the data
        filteredTime = timePoints[goodIndicesMask]
        filteredData = filteredData[goodIndicesMask]

        # Finish filtering the data
        filteredData = scipy.signal.savgol_filter(filteredData, max(3, int(self.samplingFreq*15)), 1, mode='nearest', deriv=0)
        
        return filteredTime, filteredData, goodIndicesMask

    def findStartFeatureWindow(self, timePointer, currentTime, timeWindow):
        # Loop through until you find the first time in the window 
        while self.data[0][timePointer] < currentTime - timeWindow:
            timePointer += 1
            
        return timePointer
    
    def compileBatchData(self, filteredTime, filteredData, goodIndicesMask, startFilterPointer, startFeatureTimePointer):
        assert len(goodIndicesMask) >= len(filteredData) == len(filteredTime), print(len(goodIndicesMask), len(filteredData), len(filteredTime))
        
        # Accounts for the missing points (count the number of viable points within each pointer).
        startReferenceFinger = (goodIndicesMask[0:startFeatureTimePointer - startFilterPointer]).sum(axis = 0, dtype=int)
        endReferenceFinger = startReferenceFinger + (goodIndicesMask[startFeatureTimePointer - startFilterPointer:self.lastAnalyzedDataInd+1 - startFilterPointer]).sum(axis = 0, dtype=int)
        # Compile the information in the interval.
        intervalTimes = filteredTime[startReferenceFinger:endReferenceFinger]
        intervalData = filteredData[startReferenceFinger:endReferenceFinger]

        return intervalTimes, intervalData
    
    # ---------------------------------------------------------------------- #
    # --------------------- Feature Extraction Methods --------------------- #
    
    def extractFeatures(self, timePoints, data):
        
        # ----------------------- Data Preprocessing ----------------------- #
        
        # Normalize the data
        standardizedData = (data - np.mean(data))/np.std(data, ddof=1)
                
        # Calculate the power spectral density (PSD) of the signal. USE NORMALIZED DATA
        powerSpectrumDensityFreqs, powerSpectrumDensity = scipy.signal.welch(standardizedData, fs=self.samplingFreq, window='hann', nperseg=int(self.samplingFreq*4), noverlap=None,
                                                                             nfft=None, detrend='constant', return_onesided=True, scaling='density', axis=-1, average='mean')
        powerSpectrumDensity_Normalized = powerSpectrumDensity/np.sum(powerSpectrumDensity)
        
        # ------------------------------------------------------------------ #  
        # ----------------------- Features from Data ----------------------- #
        
        # General Shape Parameters
        meanSignal = np.mean(data)
        signalEntropy = scipy.stats.entropy(abs(data))
        standardDeviation = np.std(data, ddof = 1)
        signalSkew = scipy.stats.skew(data, bias=False)
        signalKurtosis = scipy.stats.kurtosis(data, fisher=True, bias = False)
        
        # Other pamaeters
        signalChange = data[-1] - data[0]
        averageNoise = np.mean(abs(np.diff(data)))
        averageSquaredNoise = np.mean(np.diff(data)**2) / np.mean(np.diff(timePoints)**2)
        signalPower = np.trapz(data**2, timePoints) / (timePoints[-1] - timePoints[0])
        
        # ------------------------------------------------------------------ #  
        # ----------------- Features from Normalized Data ------------------ #
        baselineDataX = timePoints - timePoints[0]
        baselineDataY = data - data[0]
                
        signalSlope, slopeIntercept = np.polyfit(baselineDataX, baselineDataY, 1)        
        
        # ------------------------------------------------------------------ #  
        # ----------------------- Organize Features ------------------------ #
        
        temperatureFeatures = []
        # Add peak shape parameters
        temperatureFeatures.extend([meanSignal, signalEntropy, standardDeviation, signalSkew, signalKurtosis])
        temperatureFeatures.extend([signalChange, averageNoise, averageSquaredNoise, signalPower])
        
        # Add normalized features
        temperatureFeatures.extend([signalSlope, slopeIntercept])
        
        return temperatureFeatures


    
    
    
    
    