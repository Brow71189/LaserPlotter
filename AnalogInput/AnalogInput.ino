/*
  Analog Input
 Demonstrates analog input by reading an analog sensor on analog pin 0 and
 turning on and off a light emitting diode(LED)  connected to digital pin 13.
 The amount of time the LED will be on and off depends on
 the value obtained by analogRead().

 The circuit:
 * Potentiometer attached to analog input 0
 * center pin of the potentiometer to the analog pin
 * one side pin (either one) to ground
 * the other side pin to +5V
 * LED anode (long leg) attached to digital output 13
 * LED cathode (short leg) attached to ground

 * Note: because most Arduinos have a built-in LED attached
 to pin 13 on the board, the LED is optional.


 Created by David Cuartielles
 modified 30 Aug 2011
 By Tom Igoe

 This example code is in the public domain.

 http://www.arduino.cc/en/Tutorial/AnalogInput

 */

int sensorPin = A0;    // select the input pin for the potentiometer
//int ledPin = 13;      // select the pin for the LED
int sensorValue = 0;  // variable to store the value coming from the sensor
int MotorPin1 = 7;
int MotorPin2 = 8;
int MotorPin1State = 0;
int MotorPin2State = 1;
int counter = 10000;
int lastSensorValue = 0;

void setup() {
  // declare the ledPin as an OUTPUT:
  pinMode(MotorPin1, OUTPUT);
  pinMode(MotorPin2, OUTPUT);
  lastSensorValue = analogRead(sensorPin);
  Serial.begin(115200);
  digitalWrite(MotorPin1, HIGH);
  digitalWrite(MotorPin2, LOW);
}

void loop() {
  // read the value from the sensor:
  sensorValue = analogRead(sensorPin);
//  if (sensorValue > 200) {
//    if (lastSensorValue <= 200) {
//      counter += 1;
//    }
//  }
//  lastSensorValue = sensorValue;
//  if (counter >= 1000) {
//    counter = 0;
//    if (MotorPin1State == 0) {
//      digitalWrite(MotorPin1, HIGH);
//      MotorPin1State = 1;
//    } else {
//      digitalWrite(MotorPin1, LOW);
//      MotorPin1State = 0;
//    }
//    if (MotorPin2State == 0) {
//      digitalWrite(MotorPin2, HIGH);
//      MotorPin2State = 1;
//    } else {
//      digitalWrite(MotorPin2, LOW);
//      MotorPin2State = 0;
//    } 
//  }
  //Serial.println(counter);
  Serial.println(sensorValue);
  //delay(10);
  // turn the ledPin on
  //digitalWrite(ledPin, HIGH);
  // stop the program for <sensorValue> milliseconds:
  //delay(sensorValue);
  // turn the ledPin off:
  //digitalWrite(ledPin, LOW);
  // stop the program for for <sensorValue> milliseconds:
  //delay(sensorValue);
}
