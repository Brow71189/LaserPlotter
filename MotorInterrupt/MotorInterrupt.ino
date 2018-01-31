#include <EEPROM.h>

volatile long counterA = 0;
volatile long counterB = 0;
long target = 0;
char motor;
int not_moved = 0;
float speedA = 10.0*378.21; // in steps per second
float speedB = 10.0*11.71; // in steps per second
byte PWMA = 127;
byte PWMB = 127;
const byte PWMTolerance = 20;
volatile unsigned long last_timeA = 0;
volatile unsigned long last_timeB = 0;
volatile unsigned long this_timeA = 0;
volatile unsigned long this_timeB = 0;
volatile unsigned char* MotorBank = &PORTB;
volatile unsigned char* SensorBank = &PIND;
byte MotorAPin1 = 8;
byte MotorAPin2 = 9;
byte MotorBPin1 = 12;
byte MotorBPin2 = 13;
bool LaserState = false;
const byte LaserPin = 7;
const byte InterruptPinA = 2;
const byte InterruptPinB = 3;
const byte PWMPinA = 10;
const byte PWMPinB = 11;
const byte SensorPinA = 4;
const byte SensorPinB = 5;
byte verbosity = 1; //0: Only send necessary status messages, 1: Also send information, 2: show debug info
short last_direction = 0;
float slopeA = 0;
float slopeB = 0;
float offsetA;
float offsetB;
const byte magic_number = 42;

void setup()
{
  pinMode(MotorAPin1, OUTPUT);
  pinMode(MotorAPin2, OUTPUT);
  pinMode(MotorBPin1, OUTPUT);
  pinMode(MotorBPin2, OUTPUT);
  pinMode(LaserPin, OUTPUT);
  pinMode(SensorPinA, INPUT);
  pinMode(SensorPinB, INPUT);
  if (*MotorBank == PORTB) {
    MotorAPin1 -= 8;
    MotorAPin2 -= 8;
    MotorBPin1 -= 8;
    MotorBPin2 -= 8;
  }
  attachInterrupt(digitalPinToInterrupt(InterruptPinA), countA, RISING);
  attachInterrupt(digitalPinToInterrupt(InterruptPinB), countB, CHANGE);
  load_from_EEPROM();
  Serial.begin(115200);
  Serial.setTimeout(100);
}

void loop()
{ 
  if(Serial.available()) {
    process_line();
    if (target != 0) {
      char res = move_to(motor, &target);
      target = 0;
      Serial.write(res);
    }
  }
}
// X: move motor, V: set verbosity, R: ready check, P: get position, L: set laser state (for movements),
// F: switch laser on/off (immediately), C: set counter, S: set speed, D: do speed calibration   
void process_line() {
  char cmd = Serial.read();
  char motor_id;
  switch(cmd) {
    case 'X': while (!Serial.available()) {
                delayMicroseconds(5);
              }
              motor = Serial.read(); target = Serial.parseInt(); break;
    case 'V': verbosity = Serial.parseInt(); Serial.write(cmd); return;
    case 'R': Serial.write(cmd); return;
    case 'P': while (!Serial.available()) {
                delayMicroseconds(5);
              }
              motor_id = Serial.read();
              switch (motor_id) {
                case 'A': Serial.print(counterA); Serial.write('P'); break;
                case 'B': Serial.print(counterB); Serial.write('P'); break;
                default: if (verbosity > 0) {
                           Serial.print("Invalid motor ID: "); Serial.println(motor_id);
                         }
                         Serial.write('E'); break;
              }
              return;
	   case 'L': LaserState = (bool)Serial.parseInt(); Serial.write('L'); return;
     case 'F': if (digitalRead(LaserPin)) {
                  digitalWrite(LaserPin, LOW);
                  Serial.write('0');
                } else {
                  digitalWrite(LaserPin, HIGH);
                  Serial.write('1');
                }
                Serial.write('F');
                return;
            
     case 'C': while (!Serial.available()) {
    		        delayMicroseconds(5);
    	          }
    			    motor_id = Serial.read();
    			    switch (motor_id) {
    				      case 'A': counterA = Serial.parseInt(); Serial.write('C'); break;
    				      case 'B': counterB = Serial.parseInt(); Serial.write('C'); break;
    				      default: if (verbosity > 0) {
    					                Serial.print("Invalid motor ID: "); Serial.println(motor_id);
    				                }
    						            Serial.write('E'); break;
    			  }
           return;
     case 'S': while (!Serial.available()) {
    		        delayMicroseconds(5);
    	         }
    			     motor_id = Serial.read();
    			     switch (motor_id) {
    				      case 'A': speedA = Serial.parseFloat(); Serial.write('S'); break;
    				      case 'B': speedB = Serial.parseFloat(); Serial.write('S'); break;
    				      default: if (verbosity > 0) {
    					             Serial.print("Invalid motor ID: "); Serial.println(motor_id);
    				               }
    						           Serial.write('E'); break;
    			      }
                return;
      case 'D': char res = calibrate_speeds(); Serial.write(res); return;
  }
  if (verbosity > 0) {
    Serial.print(cmd);
    Serial.print(motor);
    Serial.println(target);
  }
}
  
char move_to(char motor_id, long* target_pos) {
  if (verbosity > 0) {
    Serial.print("Moving motor "); Serial.print(motor_id); Serial.print(" to "); Serial.println(*target_pos);
  }
  char return_value = 'X';
  volatile long* counter;
  int backlashSteps;
  byte MotorPin1;
  byte MotorPin2;
  byte PWMPin;
  byte* PWMValue;
  byte MaxPWMValue;
  byte MinPWMValue;
  float target_speed;
  int blockedThreshold;
  volatile unsigned long* last_time;
  volatile unsigned long* this_time;
  bool has_calibration = false;
  switch (motor_id) {
      case 'A': if (slopeA > 0) {
                  PWMA = (byte)round(speedA*slopeA + offsetA);
                  has_calibration = true;
                }
                PWMValue = &PWMA;
                counter = &counterA; MotorPin1 = MotorAPin1; MotorPin2 = MotorAPin2; PWMPin = PWMPinA;
                blockedThreshold = 300; target_speed = speedA; last_time = &last_timeA;
                this_time = &this_timeA; backlashSteps = 150; break;
      case 'B': if (slopeB > 0) {
                  PWMB = (byte)round(speedB*slopeB + offsetB);
                  has_calibration = true;
                }
                PWMValue = &PWMB;
                counter = &counterB; MotorPin1 = MotorBPin1; MotorPin2 = MotorBPin2; PWMPin = PWMPinB;
                blockedThreshold = 24; target_speed = speedB; last_time = &last_timeB;
                this_time = &this_timeB; backlashSteps = 0; break;
      default: if (verbosity > 0) {
                 Serial.print("Invalid motor ID: "); Serial.println(motor_id);
               }
               return 'E';
    }
  if (*PWMValue < 255-PWMTolerance && has_calibration) {
    MaxPWMValue = *PWMValue+PWMTolerance;
  } else {
    MaxPWMValue = 255;
  }

  if (*PWMValue > PWMTolerance && has_calibration) {
    MinPWMValue = *PWMValue-PWMTolerance; 
  } else {
    MinPWMValue = 0;
  }
  Serial.println(*PWMValue);Serial.println(MaxPWMValue);
  Serial.println(MinPWMValue);
  
  float current_speed = target_speed;
  long difference = *counter - *target_pos;
  if (last_direction > 0 && difference < 0) {
    *counter -= backlashSteps;
  } else if (last_direction < 0 && difference > 0) {
    *counter += backlashSteps;
  }

  if (difference < 0) {
    last_direction = -1;
  } else if (difference > 0) {
    last_direction = 1;
  } else {
    last_direction = 0;
  }
  long current_position = *counter;
  long last_position = *counter;
  unsigned long last_loop_time = micros();
  if (LaserState) {
    //*SensorBank |= 1<<LaserPin;
    digitalWrite(LaserPin, HIGH);
  } else {
    //*SensorBank &= ~(1<<LaserPin);
    digitalWrite(LaserPin, LOW);
  }
  while (difference != 0) {
    unsigned long now = micros();
	  current_position = *counter;
	  difference = current_position - *target_pos;
  	if (last_position != current_position || (now - last_loop_time) > 2.0e6/target_speed ) { // only update speed if counter changed since last time or if more time passed than we would expect for the given speed
      unsigned long time_diff = *this_time - *last_time;
      if (time_diff > 0) {
        current_speed = 1.0 / (float)(time_diff) * 1e6;  
      }
            
  	  if (verbosity > 1) {
        Serial.print("Current speed: "); Serial.print(current_speed); Serial.write(" "); Serial.print(last_position-current_position); Serial.write(" "); Serial.print(*PWMValue); Serial.write(" "); Serial.print(time_diff); Serial.write(" "); Serial.println(target_speed);
  	  }
  	  if (last_position == current_position) {
        not_moved++;
        if (not_moved > 3) {
          current_speed = 0;
        }
        if (verbosity > 1) {
          Serial.print("Increasing not moved counter to: "); Serial.println(not_moved);
        }
        if (not_moved > blockedThreshold) {
          if (verbosity > 0) {
            Serial.print("Motor might be blocked. Stopping. ");
            Serial.println(*counter);
          } else {
            return_value = 'B';
          }
          not_moved = 0;
          break;
          }
        } else {
          not_moved = 0;
        }
	  
  	  if ((difference < 0 && (last_position-current_position) > 0) || (difference > 0 && (last_position-current_position) < 0)) {
        current_speed = target_speed + 1;
  	  }
  	
  	  if (current_speed > target_speed && *PWMValue > MinPWMValue) {
  		  (*PWMValue)--;
  	  } else if (current_speed < target_speed && *PWMValue < MaxPWMValue) {
  		  (*PWMValue)++;
  	  }
	
	
    
      if (difference > 0) {
          *MotorBank |= 1<<MotorPin1;
          *MotorBank &= ~(1<<MotorPin2);
      }
      else {
          *MotorBank |= 1<<MotorPin2;
          *MotorBank &= ~(1<<MotorPin1);
      }
      analogWrite(PWMPin, *PWMValue);
  	  last_loop_time = now;
  	  last_position = current_position;
	  }
  }
  digitalWrite(LaserPin, LOW);
  *MotorBank |= 1<<MotorPin1;
  *MotorBank |= 1<<MotorPin2;
  last_timeA = 0;
  this_timeA = 0;
  last_timeB = 0;
  this_timeB = 0;
  if (verbosity > 0) {
    delay(500);
    Serial.print("Done "); Serial.println(*counter);
  }
  
  return return_value;
}

char calibrate_speeds() {
  char movement_result;
  byte PWMValuesA[5];
  byte PWMValuesB[5];
  float speedsA[] = {speedA/8, speedA/4, speedA/2, speedA, speedA*2};
  float speedsB[] = {speedB/8, speedB/4, speedB/2, speedB, speedB*2};
  slopeA = 0;
  slopeB = 0;
  
  target = 0;
  movement_result = move_to('A', &target);
  if (movement_result != 'X') {
    return movement_result;
  }
  movement_result = move_to('B', &target);
  if (movement_result != 'X') {
    return movement_result;
  }
  for (byte i=0; i<5; i++) {
    target = (long)round(speedsA[i]);
    speedA = speedsA[i];
    movement_result = move_to('A', &target);
    if (movement_result != 'X') {
      speedA = speedsA[3];
      return movement_result;
    }
    PWMValuesA[i] = PWMA;
  }
  speedA = speedsA[3];

  for (byte i=0; i<5; i++) {
    target = (long)round(speedsB[i]);
    speedB = speedsB[i];
    movement_result = move_to('B', &target);
    if (movement_result != 'X') {
      speedB = speedsB[3];
      return movement_result;
    }
    PWMValuesB[i] = PWMB;
  }
  speedB = speedsB[3];
  //calculate average slope
  for (byte i=0; i<4; i++) {
     slopeA += ((float)(PWMValuesA[i+1] - PWMValuesA[i]) / (speedsA[i+1] - speedsA[i]))/4;
     slopeB += ((float)(PWMValuesB[i+1] - PWMValuesB[i]) / (speedsB[i+1] - speedsB[i]))/4;
  }
  //use one point to find offset
  offsetA = (float)PWMValuesA[0] - slopeA*speedsA[0];
  offsetB = (float)PWMValuesB[0] - slopeB*speedsB[0];
  save_to_EEPROM();
  target = 0;
  movement_result = move_to('A', &target);
  movement_result = move_to('B', &target);
  return 'D';
}

void save_to_EEPROM() {
  save_to_EEPROM(0);
}

void save_to_EEPROM(int start_address) {
  unsigned int addr = start_address;
  EEPROM.update(addr, magic_number);
  addr++;
  float* to_save[] = {&slopeA, &offsetA, &slopeB, &offsetB};
  for (byte i=0; i<4; i++) {
    EEPROM.put(addr, *to_save[i]); 
    addr += sizeof(float);
  }
}

void load_from_EEPROM() {
  unsigned int addr;
  for (addr=0; addr < EEPROM.length(); addr++) {
    if (EEPROM.read(addr) == magic_number) {
      break;
    }
  }
  addr++;
  if (addr >= EEPROM.length() - 16) {
    return;
  }

  float* to_read[] = {&slopeA, &offsetA, &slopeB, &offsetB};
  float read_value;
  for (byte i=0; i<4; i++) {
    EEPROM.get(addr, read_value);
    *to_read[i] = read_value;
    addr += sizeof(float);
  }
  
  
}

void countA()
// This is triggering on the rising flank so we just have to check the value of the second sensor pin to determine the direction.
{ 
  if (*SensorBank&1<<SensorPinA) {
    last_timeA = this_timeA;
    this_timeA = micros();
    counterA--;
  } else {
    last_timeA = this_timeA;
    this_timeA = micros();
    counterA++;
  }
}

void countB()
// This triggers on both flanks. If we check whether both pins are in the same state or opposite we can determine the direction 
{ 
  if (((*SensorBank&1<<InterruptPinB)>>InterruptPinB) ^ ((*SensorBank&1<<SensorPinB)>>SensorPinB)) {
    last_timeB = this_timeB;
    this_timeB = micros();
    counterB--;
  } else {
    last_timeB = this_timeB;
    this_timeB = micros();
    counterB++;
  }
}
