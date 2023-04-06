
# -------------------------------------------------------------------------- #
# ---------------------------- Imported Modules ---------------------------- #

# Basic Modules
import scipy
import numpy as np
# Feature Extraction Modules
import eeglib
import antropy

# Import Files
import _globalProtocol
        
# ---------------------------------------------------------------------------#
# ---------------------------------------------------------------------------#

class gsrProtocol(_globalProtocol.globalProtocol):
    
    def __init__(self, numPointsPerBatch = 3000, moveDataFinger = 10, numChannels = 2, plottingClass = None, readData = None):        
        # Feature collection parameters
        self.featureTimeWindow_Tonic = 60        # The duration of time that each feature considers.
        self.featureTimeWindow_Phasic = 15       # The duration of time that each feature considers.
        # Filter Parameters
        self.tonicFrequencyCutoff = 0.05   # Maximum tonic component frequency.
        self.dataPointBuffer = 5000        # A Prepended Buffer in the Filtered Data that Represents BAD Filtering; Units: Points
        self.cutOffFreq = [None, 15]       # Filter cutoff frequencies: [HPF, LPF].
        
        # Initialize common model class
        super().__init__(numPointsPerBatch, moveDataFinger, numChannels, plottingClass, readData)
        
    def resetAnalysisVariables(self):
        # General parameters
        self.startFeatureTimePointer_Tonic = 0    # The start pointer of the feature window interval.
        self.startFeatureTimePointer_Phasic = 0    # The start pointer of the feature window interval.
            
    def checkParams(self):
        assert self.featureTimeWindow_Tonic < self.dataPointBuffer, "The buffer does not include enough points for the feature window"
        assert self.featureTimeWindow_Phasic < self.dataPointBuffer, "The buffer does not include enough points for the feature window"
        
    def setSamplingFrequencyParams(self):
        maxFeatureTimeWindow = max(self.featureTimeWindow_Tonic, self.featureTimeWindow_Phasic)
        # Set Parameters
        self.minPointsPerBatchTonic = int(self.samplingFreq*self.featureTimeWindow_Tonic/2)
        self.minPointsPerBatchPhasic = int(self.samplingFreq*self.featureTimeWindow_Phasic*3/4)
        self.lastAnalyzedDataInd = int(self.samplingFreq*maxFeatureTimeWindow)
        self.dataPointBuffer = max(self.dataPointBuffer, int(self.samplingFreq*15))

    def initPlotPeaks(self): 
        # Establish pointers to the figure
        self.fig = self.plottingClass.fig
        axes = self.plottingClass.axes['gsr'][0]

        # Plot the Raw Data
        yLimLow = 1E-6; yLimHigh = 1E-5; 
        self.bioelectricDataPlots = []; self.bioelectricPlotAxes = []
        for channelIndex in range(self.numChannels):
            # Create Plots
            if self.numChannels == 1:
                self.bioelectricPlotAxes.append(axes[0])
            else:
                self.bioelectricPlotAxes.append(axes[channelIndex, 0])
            
            # Generate Plot
            self.bioelectricDataPlots.append(self.bioelectricPlotAxes[channelIndex].plot([], [], '-', c="purple", linewidth=1, alpha = 0.65)[0])
            
            # Set Figure Limits
            self.bioelectricPlotAxes[channelIndex].set_ylim(yLimLow, yLimHigh)
            # Label Axis + Add Title
            self.bioelectricPlotAxes[channelIndex].set_ylabel("GSR (Siemens)", fontsize=13, labelpad = 10)
            
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
            self.filteredBioelectricDataPlots.append(self.filteredBioelectricPlotAxes[channelIndex].plot([], [], '-', c="purple", linewidth=1, alpha = 0.65)[0])

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
            
            # Extract sampling frequency from the first batch of data
            if not self.samplingFreq:
                self.setSamplingFrequency(startFilterPointer)
                
            # Filter the data and remove bad indices
            filteredTime, filteredData, goodIndicesMask = self.filterData(timePoints, dataBuffer)
            
            # Seperate the tonic (baseline) from the phasic (peaks) data
            tonicComponent, phasicComponent = self.splitPhasicTonic(filteredData)
            # --------------------------------------------------------------- #
            
            # ---------------------- Feature Extraction --------------------- #
            if self.collectFeatures:
                # Confirm assumptions made about GSR feature extraction
                assert dataFinger <= self.lastAnalyzedDataInd, str(dataFinger) + "; " + str(self.lastAnalyzedDataInd) # We are NOT analyzing data in the buffer region. self.startTimePointerSCL CAN be in the buffer region.
                
                # Extract features across the dataset
                while self.lastAnalyzedDataInd < len(self.data[0]):
                    featureTime = self.data[0][self.lastAnalyzedDataInd]
                    
                    # Find the start window pointer and get the data.
                    self.startFeatureTimePointer_Tonic = self.findStartFeatureWindow(self.startFeatureTimePointer_Tonic, featureTime, self.featureTimeWindow_Tonic)
                    self.startFeatureTimePointer_Phasic = self.findStartFeatureWindow(self.startFeatureTimePointer_Phasic, featureTime, self.featureTimeWindow_Phasic)                    
                    # Compile the well-fromed data in the feature interval.
                    intervalTimesTonic, intervalTonicData = self.compileBatchData(filteredTime, tonicComponent, goodIndicesMask, startFilterPointer, self.startFeatureTimePointer_Tonic)
                    intervalTimesPhasic, intervalPhasicData = self.compileBatchData(filteredTime, phasicComponent, goodIndicesMask, startFilterPointer, self.startFeatureTimePointer_Phasic)
                    
                    # Only extract features if enough information is provided.
                    if self.minPointsPerBatchTonic < len(intervalTimesTonic) and self.minPointsPerBatchPhasic < len(intervalTimesPhasic):
                        # Calculate the features in this window.
                        gsrFeatures = self.extractTonicFeatures(intervalTimesTonic, intervalTonicData)
                        gsrFeatures.extend(self.extractPhasicFeatures(intervalTimesPhasic, intervalPhasicData))
                        # Keep track of the new features.
                        self.readData.averageFeatures([featureTime], [gsrFeatures], self.featureTimes, self.rawFeatures, self.compiledFeatures, self.featureAverageWindow)
                
                    # Keep track of which data has been analyzed 
                    self.lastAnalyzedDataInd += int(self.samplingFreq*10)
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
        # Filter the data: LPF and moving average (Savgol) filter
        filteredData = self.filteringMethods.bandPassFilter.butterFilter(data, self.cutOffFreq[1], self.samplingFreq, order = 1, filterType = 'low')
        #filteredData = scipy.signal.savgol_filter(filteredData, max(int(self.samplingFreq*5), 3), 1, mode='nearest', deriv=0)
        filteredTime = timePoints.copy()
        
        return filteredTime, filteredData, np.ones(len(filteredTime))
    
    def splitPhasicTonic(self, data):
        # Isolate the tonic component (baseline) of the GSR
        tonicComponent = self.filteringMethods.bandPassFilter.butterFilter(data, self.tonicFrequencyCutoff, self.samplingFreq, order = 1, filterType = 'low')
        # Extract the phasic component (peaks) of the GSR
        phasicComponent = tonicComponent - data
        
        return tonicComponent, phasicComponent
    
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
                    
    def extractTonicFeatures(self, timePoints, data):
        # ----------------------- Data Preprocessing ----------------------- #
        
        # Normalize the data
        standardizedData = (data - np.mean(data))/np.std(data, ddof=1)
        
        # Calculate the derivatives
        firstDeriv = np.gradient(standardizedData, timePoints)
        secondDeriv = np.gradient(firstDeriv, timePoints)
        
        # ------------------------------------------------------------------ #  
        # ----------------------- Features from Data ----------------------- #
        
        # General Shape Parameters
        meanSignal = np.mean(data)
        signalEntropy = scipy.stats.entropy(abs(data + 10E-50))
        standardDeviation = np.std(data, ddof = 1)
        signalSkew = scipy.stats.skew(data, bias=False)
        signalKurtosis = scipy.stats.kurtosis(data, fisher=True, bias = False)
        normalizedArea = scipy.integrate.simpson(data, timePoints)/len(timePoints)
        
        # Other pamaeters
        signalChange = data[-1] - data[0]
        maxChange = max(data) - min(data)
        averageNoise = np.mean(abs(np.diff(data)))
        averageSquaredNoise = np.mean(np.diff(data)**2)/len(timePoints)
        signalPower = scipy.integrate.simpson(data**2, timePoints)/len(timePoints)
        
        centralMoment = scipy.stats.moment(data, moment=1)
        arcLength = np.sqrt(1 + np.diff(data))
        rootMeaSquared = np.sqrt(signalPower)
        
        # areaPerimeter =  
        
        # ------------------------------------------------------------------ #  
        # -------------------- Features from Derivatives ------------------- #
        
        # First derivative features
        firstDerivMean = np.mean(firstDeriv)
        firstDerivSTD = np.std(firstDeriv, ddof = 1)
        firstDerivPower = scipy.integrate.simpson(firstDeriv**2, timePoints)/len(timePoints)
        
        # Second derivative features
        secondDerivMean = np.mean(secondDeriv)
        secondDerivSTD = np.std(secondDeriv, ddof = 1)
        secondDerivPower = scipy.integrate.simpson(secondDeriv**2, timePoints)/len(timePoints)
        
        # ------------------------------------------------------------------ #  
        # ----------------- Features from Normalized Data ------------------ #
        baselineDataX = timePoints - timePoints[0]
        baselineDataY = data - meanSignal
                
        signalSlope, slopeIntercept = np.polyfit(baselineDataX, baselineDataY, 1)     
        
        # fequencyProfile = scipy.fft.fft(data)
        
        # 0.1 to 0.2 (F1SC), 0.2 to 0.3 (F2SC) and 0.3 to 0.4 (F3SC)

        
        # ------------------------------------------------------------------ #  
        # ----------------------- Organize Features ------------------------ #
        
        gsrFeatures = []
        # Add peak shape parameters
        gsrFeatures.extend([meanSignal, signalEntropy, standardDeviation, signalSkew, signalKurtosis, normalizedArea])
        gsrFeatures.extend([signalChange, maxChange, averageNoise, averageSquaredNoise, signalPower])
        
        # # Add derivative features
        gsrFeatures.extend([firstDerivMean, firstDerivSTD, firstDerivPower])
        gsrFeatures.extend([secondDerivMean, secondDerivSTD, secondDerivPower])
        
        # Add normalized features
        gsrFeatures.extend([signalSlope, slopeIntercept])

        return gsrFeatures
            
    def extractPhasicFeatures(self, timePoints, data):
        
        # ----------------------- Data Preprocessing ----------------------- #
        
        # Normalize the data
        standardizedData = (data - np.mean(data))/np.std(data, ddof=1)
                
        # Calculate the power spectral density (PSD) of the signal. USE NORMALIZED DATA
        powerSpectrumDensityFreqs, powerSpectrumDensity = scipy.signal.welch(standardizedData, fs=self.samplingFreq, window='hann', nperseg=int(self.samplingFreq*4), noverlap=None,
                                                                             nfft=None, detrend='constant', return_onesided=True, scaling='density', axis=-1, average='mean')
        powerSpectrumDensity_Normalized = powerSpectrumDensity/np.sum(powerSpectrumDensity)
        
        # ------------------------------------------------------------------ #  
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
        deltaPower, thetaPower, alphaPower, betaPower, gammaPower = self.universalMethods.bandPower(powerSpectrumDensity, powerSpectrumDensityFreqs, bands = [(1, 4), (4, 8), (8, 12), (12, 30), (30, 100)])
        muPower, beta1Power, beta2Power, beta3Power, smrPower = self.universalMethods.bandPower(powerSpectrumDensity, powerSpectrumDensityFreqs, bands = [(9, 11), (13, 16), (16, 20), (20, 28), (13, 15)])
        # Calculate band wave power ratios
        engagementLevelEst = betaPower/(alphaPower + thetaPower)
        
        # Number of zero-crossings
        num_zerocross = antropy.num_zerocross(data)
        
        # ------------------------------------------------------------------ #
        gsrFeatures = []
        
        # Feature Extraction: Hjorth
        gsrFeatures.extend([hjorthActivity, hjorthMobility, hjorthComplexity, firstDerivVariance, secondDerivVariance])
        gsrFeatures.extend([hjorthActivityPSD, hjorthMobilityPSD, hjorthComplexityPSD, firstDerivVariancePSD, secondDerivVariancePSD])
        # Feature Extraction: Entropy
        gsrFeatures.extend([perm_entropy, spectral_entropy, svd_entropy])
        # Feature Extraction: Fractal
        gsrFeatures.extend([petrosian_fd, katz_fd, higuchi_fd, DFA, LZC])
        # Feature Extraction: Other
        gsrFeatures.extend([deltaPower, thetaPower, alphaPower, betaPower, gammaPower])
        gsrFeatures.extend([muPower, beta1Power, beta2Power, beta3Power, smrPower])
        gsrFeatures.extend([engagementLevelEst, num_zerocross])
        
        return gsrFeatures




    
    
    
    
    