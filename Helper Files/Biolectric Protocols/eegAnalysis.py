
# -------------------------------------------------------------------------- #
# ---------------------------- Imported Modules ---------------------------- #

# Basic Modules
import scipy
import sklearn
import numpy as np
# Feature Extraction Modules
import eeglib
import antropy

# Import Files
import _globalProtocol

# ---------------------------------------------------------------------------#
# ---------------------------------------------------------------------------#

class eegProtocol(_globalProtocol.globalProtocol):
    
    def __init__(self, numPointsPerBatch = 3000, moveDataFinger = 10, numChannels = 2, plottingClass = None, readData = None):
        # Feature collection parameters
        self.featureTimeWindow = 15         # The duration of time that each feature considers;

        # Filter parameters.
        self.cutOffFreq = [0.05, 50]        # Optimal LPF Cutoff in Literatrue is 6-8 or 20 Hz (Max 35 or 50); I Found 25 Hz was the Best, but can go to 15 if noisy (small amplitude cutoff)
        self.dataPointBuffer = 0            # The number of previouy analyzed points. Used as a buffer for filtering.
        # High-pass filter parameters.
        self.stopband_edge = 1           # Common values for EEG are 1 Hz and 2 Hz. If you need to remove more noise, you can choose a higher stopband edge frequency. If you need to preserve the signal more, you can choose a lower stopband edge frequency.
        self.passband_ripple = 0.1       # Common values for EEG are 0.1 dB and 0.5 dB. If you need to remove more noise, you can choose a lower passband ripple. If you need to preserve the signal more, you can choose a higher passband ripple.
        self.stopband_attenuation = 60   # Common values for EEG are 40 dB and 60 dB. If you need to remove more noise, you can choose a higher stopband attenuation. If you need to preserve the signal more, you can choose a lower stopband attenuation.

        # Initialize common model class
        super().__init__(numPointsPerBatch, moveDataFinger, numChannels, plottingClass, readData)
        
    def resetAnalysisVariables(self):
        # General parameters 
        self.startFeatureTimePointer = 0    # The start pointer of the feature window interval.
            
    def checkParams(self):
        pass
    
    def setSamplingFrequencyParams(self):
        # Set Parameters
        self.lastAnalyzedDataInd = int(self.samplingFreq*self.featureTimeWindow)
        self.minPointsPerBatch = int(self.samplingFreq*self.featureTimeWindow*3/4)
        self.dataPointBuffer = max(self.dataPointBuffer, int(self.samplingFreq*100)) # cutOffFreq = 0.1, use 70 seconds; cutOffFreq = 0.01, use 400 seconds; cutOffFreq = 0.05, use 100 seconds

    def initPlotPeaks(self): 
        # Establish pointers to the figure
        self.fig = self.plottingClass.fig
        axes = self.plottingClass.axes['eeg'][0]

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
            self.bioelectricDataPlots.append(self.bioelectricPlotAxes[channelIndex].plot([], [], '-', c="tab:green", linewidth=1, alpha = 0.65)[0])
            
            # Set Figure Limits
            self.bioelectricPlotAxes[channelIndex].set_ylim(yLimLow, yLimHigh)
            # Label Axis + Add Title
            self.bioelectricPlotAxes[channelIndex].set_ylabel("EEG Signal (Volts)", fontsize=13, labelpad = 10)
            
        # Create the Data Plots
        self.filteredBioelectricDataPlots = []
        self.filteredBioelectricPlotAxes = [] 
        yLimLow = -1.65; yLimHigh = 1.65; 
        for channelIndex in range(self.numChannels):
            # Create Plot Axes
            if self.numChannels == 1:
                self.filteredBioelectricPlotAxes.append(axes[1])
            else:
                self.filteredBioelectricPlotAxes.append(axes[channelIndex, 1])
            
            # Plot Flitered Peaks
            self.filteredBioelectricDataPlots.append(self.filteredBioelectricPlotAxes[channelIndex].plot([], [], '-', c="tab:green", linewidth=1, alpha = 0.65)[0])

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
            # -------------------------------------------------------------- #
            
            # ---------------------- Feature Extraction --------------------- #
            if self.collectFeatures:    
                # Extract features across the dataset
                while self.lastAnalyzedDataInd < len(self.data[0]):
                    featureTime = self.data[0][self.lastAnalyzedDataInd]
                    
                    # Find the start window pointer.
                    self.startFeatureTimePointer = self.findStartFeatureWindow(self.startFeatureTimePointer, featureTime, self.featureTimeWindow)
                    # Compile the good data in the feature interval.
                    intervalTimes, intervalData = self.compileBatchData(filteredTime, filteredData, goodIndicesMask, startFilterPointer, self.startFeatureTimePointer)
                    
                    # Only extract features if enough information is provided.
                    if self.minPointsPerBatch < len(intervalTimes):
                        # Calculate and save the features in this window.
                        eegFeatures = self.extractFeatures(intervalTimes, intervalData)
                        self.readData.averageFeatures([featureTime], [eegFeatures], self.featureTimes, self.rawFeatures, self.compiledFeatures, self.featureAverageWindow)
                
                    # Keep track of which data has been analyzed 
                    self.lastAnalyzedDataInd += int(self.samplingFreq*5)
            # -------------------------------------------------------------- #   

        
            # ------------------- Plot Biolectric Signals ------------------ #
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
            # -------------------------------------------------------------- #   
            
    def filterData(self, timePoints, data):
        # Find the bad points associated with motion artifacts
        motionIndices = np.logical_or(data < 0.1, data > 3.15)
        motionIndices_Broadened = scipy.signal.savgol_filter(motionIndices, max(3, int(self.samplingFreq*10)), 1, mode='nearest', deriv=0)
        goodIndicesMask = motionIndices_Broadened < 0.01
        
        # Filtering the whole dataset
        filteredData = self.filteringMethods.bandPassFilter.butterFilter(data, self.cutOffFreq[1], self.samplingFreq, order = 3, filterType = 'low')
        filteredData = self.filteringMethods.bandPassFilter.high_pass_filter(filteredData, self.samplingFreq, self.cutOffFreq[0], self.stopband_edge, self.passband_ripple, self.stopband_attenuation)
        # Remove the bad points from the filtered data
        filteredTime = timePoints[goodIndicesMask]
        filteredData = filteredData[goodIndicesMask]
        
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
    
    def independantropyComponentAnalysis(self, data):
        ica = sklearn.decomposition.FastICA(whiten='unit-variance')
        data = ica.fit_transform(data.reshape(-1,1)).transpose()[0]
        
        return data
    
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
        
        # ------------------- Feature Extraction: Hjorth ------------------- #
        
        # Calculate the hjorth parameters
        hjorthActivity, hjorthMobility, hjorthComplexity, firstDerivVariance, secondDerivVariance = self.universalMethods.hjorthParameters(timePoints, data)
        hjorthActivityPSD, hjorthMobilityPSD, hjorthComplexityPSD, firstDerivVariancePSD, secondDerivVariancePSD = self.universalMethods.hjorthParameters(powerSpectrumDensityFreqs, powerSpectrumDensity_Normalized)
        
        # ------------------- Feature Extraction: Entropy ------------------ #
        
        # Entropy calculation
        perm_entropy = antropy.perm_entropy(standardizedData, order = 3, delay = 1, normalize=True)      # Permutation entropy: same if standardized or not
        spectral_entropy = -np.sum(powerSpectrumDensity_Normalized*np.log2(powerSpectrumDensity_Normalized)) / np.log2(len(powerSpectrumDensity_Normalized)) # Spectral entropy = - np.sum(psd * log(psd)) / np.log(len(psd)
        svd_entropy = antropy.svd_entropy(standardizedData, order = 3, delay=1, normalize=True)          # Singular value decomposition entropy: same if standardized or not
        # app_entropy = antropy.app_entropy(data, order = 2, metric="chebyshev")             # Approximate sample entropy
        # sample_entropy = antropy.sample_entropy(data, order = 2, metric="chebyshev")       # Sample entropy
        
        # ------------------- Feature Extraction: Fractal ------------------ #
        
        # Fractal analysis
        petrosian_fd = antropy.petrosian_fd(standardizedData) # Same if standardized or not
        katz_fd = antropy.katz_fd(standardizedData) # Same if standardized or not
        higuchi_fd = antropy.higuchi_fd(x=data.astype('float64'), kmax = 10)    # Numba. Same if standardized or not
        DFA = antropy.detrended_fluctuation(data)           # Numba. Same if standardized or not
        LZC = eeglib.features.LZC(data)
        
        # ------------------- Feature Extraction: Other ------------------ #
        
        # Calculate the band wave powers
        deltaPower, thetaPower, alphaPower, betaPower, gammaPower = self.universalMethods.bandPower(powerSpectrumDensity, powerSpectrumDensityFreqs, bands = [(0.5, 4), (4, 8), (8, 12), (12, 30), (30, 100)])
        muPower, beta1Power, beta2Power, beta3Power, smrPower = self.universalMethods.bandPower(powerSpectrumDensity, powerSpectrumDensityFreqs, bands = [(8, 13), (13, 16), (16, 20), (20, 28), (13, 15)])
        # Calculate band wave power ratios
        engagementLevelEst = betaPower/(alphaPower + thetaPower)
        
        # Number of zero-crossings
        num_zerocross = antropy.num_zerocross(data)
        
        # ------------------------------------------------------------------ #
        eegFeatures = []
        
        # Feature Extraction: Hjorth
        eegFeatures.extend([hjorthActivity, hjorthMobility, hjorthComplexity, firstDerivVariance, secondDerivVariance])
        eegFeatures.extend([hjorthActivityPSD, hjorthMobilityPSD, hjorthComplexityPSD, firstDerivVariancePSD, secondDerivVariancePSD])
        # Feature Extraction: Entropy
        eegFeatures.extend([perm_entropy, spectral_entropy, svd_entropy])
        # Feature Extraction: Fractal
        eegFeatures.extend([petrosian_fd, katz_fd, higuchi_fd, DFA, LZC])
        # Feature Extraction: Other
        eegFeatures.extend([deltaPower, thetaPower, alphaPower, betaPower, gammaPower])
        eegFeatures.extend([muPower, beta1Power, beta2Power, beta3Power, smrPower])
        eegFeatures.extend([engagementLevelEst, num_zerocross])
        
        return eegFeatures
        
            