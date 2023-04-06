// ********************************** Import Libraries ********************************** //

// Fast Analog Read Library
#include "avdweb_AnalogReadFast.h"

// ******************************** Initialize Variables ******************************** //

// Time Variables
const unsigned int oneSecMicro = pow(10,6);
unsigned long beginSamplingTime;
unsigned long endSamplingTime;
unsigned int previousMicros;
unsigned int currentMicros;
unsigned int currentSecond;
// String-Form Time Variables
String currentSecond_String;
String currentMicros_String;
// Keep track of loop time
unsigned long totalLoopTime;
unsigned long startLoopTime;

// Analog read variables
const byte ADC0 = A0; // Analog Pins
int numberOfReadsADC = 30;
// ADC storage variables
float readingADC;
float readingEMG;
String readingEMG_String;

// ************************************************************************************** //
// ********************************** Helper Functions ********************************** //

String padZeros(unsigned long number, int totalLength) {
    String finalNumber = String(number);
    int numZeros = totalLength - finalNumber.length();
    for (int i = 0; i < numZeros; i++) {
      finalNumber = "0" + finalNumber;
    }
    return finalNumber;
}

int readADC(byte channel) {
    // Throw out the first result
    analogReadFast(channel);
    
    readingADC = 0.00000000;
    // Multisampling Analog Read
    for (int i = 0; i < numberOfReadsADC; i++) {
        // Stream in the Data from the Board
        readingADC += analogReadFast(channel);
    }
    // Calibrate the ADC value - BOARD SPECIFIC!
    readingADC = readingADC/numberOfReadsADC;

    return readingADC;
}

// ************************************************************************************** //
// *********************************** Arduino Setup ************************************ //

// Setup Arduino; Runs Once
void setup() {
    // Initialize Streaming
    Serial.begin(115200);     // Use 115200 baud rate for serial communication
    Serial.flush();

    // Start the Timer at Zero
    currentSecond = 0;
    previousMicros = micros();
}

// ************************************************************************************** //
// ************************************ Arduino Loop ************************************ //

// Arduino Loop; Runs Until Arduino Closes
void loop() {  
    startLoopTime = micros();
    beginSamplingTime = micros() - previousMicros;
    
    // Read the data
    readingEMG = readADC(ADC0);     // Read the voltage value of A0 port (EOG Channel1)
    endSamplingTime = micros() - previousMicros; // Record Final Time
    
    // Record the Time the Signals Were Collected (from Previous Point)
    currentMicros = (beginSamplingTime + endSamplingTime)/2;
    while (currentMicros >= oneSecMicro) {
        currentSecond += 1;
        currentMicros -= oneSecMicro;
    }

    // Convert Data into String
    readingEMG_String = padZeros(readingEMG, 4);
    // Convert Times into String
    currentSecond_String = padZeros(currentSecond, 2);
    currentMicros_String = padZeros(currentMicros, 6);
    
    // Compile Sensor Data and Send
    Serial.println(currentSecond_String + "." + currentMicros_String + "," + readingEMG_String);

    // Reset Parameters
    previousMicros = previousMicros + currentMicros + oneSecMicro*currentSecond;
    currentSecond = 0;
    // Add Delay for WiFi to Send Data
    totalLoopTime = micros() - startLoopTime;
    //if (1000 - 100 > totalLoopTime) {delayMicroseconds(1000 - totalLoopTime);}
}

