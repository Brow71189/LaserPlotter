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
const byte PWMTolerance = 50;
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
// F: switch laser on/off (immediately), C: set counter, S: set speed, D: do speed calibration, G: get calibration
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
      case 'D': {char res = calibrate_speeds(); Serial.write(res);}
                return;
      case 'G': Serial.print("SlopeA: "); Serial.print(slopeA, 4); Serial.print(", OffsetA: "); Serial.print(offsetA);
                Serial.print(", SlopeB: "); Serial.print(slopeB, 4); Serial.print(", OffsetB: "); Serial.println(offsetB);
                return;
      
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
                blockedThreshold = 200; target_speed = speedA; last_time = &last_timeA;
                this_time = &this_timeA; backlashSteps = 0; break;
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
  //Serial.println(*PWMValue);Serial.println(MaxPWMValue);
  //Serial.println(MinPWMValue);
  
  float current_speed = target_speed;
  long difference = *counter - *target_pos;
  if (last_direction > 0 && difference < 0) {
    //Serial.println("backlash left");
    *counter -= backlashSteps;
  } else if (last_direction < 0 && difference > 0) {
    //Serial.println("backlash right");
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
      //long time_diff = *this_time - *last_time;
      //if (time_diff != 0) {
      if (now - last_loop_time != 0) {
        current_speed = (float)(abs(last_position - current_position)) / (float)(now - last_loop_time) * 1e6;  
      }
            
  	  if (verbosity > 1) {
        Serial.print(*PWMValue); Serial.print(" Current speed: "); Serial.println(current_speed); //Serial.write(" "); Serial.print(last_position-current_position); Serial.write(" "); Serial.print(*PWMValue); Serial.write(" "); Serial.print(time_diff); Serial.write(" "); Serial.println(target_speed);
  	  }
  	  if (last_position == current_position) {
        not_moved++;
        if (not_moved > 2) {
          current_speed = 0;
        }
        if (verbosity > 1) {
          Serial.print("Increasing not moved counter to: "); Serial.println(not_moved);
        }
        if (not_moved > blockedThreshold) {
          if (verbosity > 0) {
            Serial.print("Motor might be blocked. Stopping. ");
            Serial.println(*counter);
          }
          return_value = 'B';
          not_moved = 0;
          break;
          }
        } else {
          not_moved = 0;
        }
	  
  	  if ((difference < 0 && (last_position-current_position) > 0) || (difference > 0 && (last_position-current_position) < 0)) {
        current_speed = 0;//target_speed + 1;
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
  //last_timeA = 0;
  //this_timeA = 0;
  //last_timeB = 0;
  //this_timeB = 0;
  if (verbosity > 0) {
    delay(500);
    Serial.print("Done "); Serial.print(*PWMValue); Serial.write(" "); Serial.println(*counter);
  }
  
  return return_value;
}

char calibrate_speeds() {
  char movement_result;
  const byte array_length = 10;
  float speedsA[] = {speedA/4, speedA/2, speedA, speedA*2, speedA*3, speedA*3, speedA*2, speedA, speedA/2, speedA/4};
  float speedsB[] = {speedB/4, speedB/2, speedB, speedB*2, speedB*3, speedB*3, speedB*2, speedB, speedB/2, speedB/4};
  byte PWMValuesA[array_length];
  byte PWMValuesB[array_length];
  slopeA = 0;
  slopeB = 0;
  speedA = speedsA[0];
  speedB = speedsB[0];
  target = (long)(counterA + ((long)2*speedA));
  movement_result = move_to('A', &target);
  if (movement_result != 'X') {
    return movement_result;
  }
  target = (long)(counterB + ((long)2*speedB));
  movement_result = move_to('B', &target);
  if (movement_result != 'X') {
    return movement_result;
  }
  for (byte i=0; i<array_length; i++) {
    if (i < array_length/2) {
      target = counterA + ((long)round(2*speedsA[i]));  
    } else {
      target = counterA - ((long)round(2*speedsA[i]));
    }
    
    speedA = speedsA[i];
    movement_result = move_to('A', &target);
    if (movement_result != 'X') {
      speedA = speedsA[2];
      target = 0;
      return movement_result;
    }
    PWMValuesA[i] = PWMA;
    delay(500);
  }
  speedA = speedsA[2];

  for (byte i=0; i<array_length; i++) {
    if (i < array_length/2) {
      target = counterB + ((long)round(2*speedsB[i])); 
    } else {
      target = counterB - ((long)round(2*speedsB[i]));
    }
    speedB = speedsB[i];
    movement_result = move_to('B', &target);
    if (movement_result != 'X') {
      speedB = speedsB[2];
      target = 0;
      return movement_result;
    }
    PWMValuesB[i] = PWMB;
    delay(500);
  }
  speedB = speedsB[2];
  //calculate average slope
  for (byte i=0; i<4; i++) {
     slopeA += ((float)(PWMValuesA[i+1] - PWMValuesA[i]) / (speedsA[i+1] - speedsA[i]))/4;
     slopeB += ((float)(PWMValuesB[i+1] - PWMValuesB[i]) / (speedsB[i+1] - speedsB[i]))/4;
  }
  //use one point to find offset
  offsetA = (float)PWMValuesA[0] - slopeA*speedsA[0];
  offsetB = (float)PWMValuesB[0] - slopeB*speedsB[0];
  char result = linreg(array_length, speedsA, PWMValuesA, &slopeA, &offsetA, NULL);
  if (result != 'D') {
    target = 0;
    return result;
  }
  result = linreg(array_length, speedsB, PWMValuesB, &slopeB, &offsetB, NULL);
  if (result != 'D') {
    target = 0;
    return result;
  }
  save_to_EEPROM();
  target = 0;
  //movement_result = move_to('A', &target);
  //movement_result = move_to('B', &target);
  if (verbosity > 0) {
    Serial.print("Motor A calibrations: ");
    for (byte i=0; i<array_length; i++) {
      Serial.print(PWMValuesA[i]);
      Serial.write(" ");
    }
    Serial.print(", Motor B calibrations: ");
    for (byte i=0; i<array_length; i++) {
      Serial.print(PWMValuesB[i]);
      Serial.write(" ");
    }
    Serial.write("\n");
  }
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
    counterA--;
  } else {
    counterA++;
  }
  last_timeA = this_timeA;
  this_timeA = micros();
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

char linreg(byte n, const float x[], const byte y[], float* m, float* b, float* r){
    float   sumx = 0.0;                      /* sum of x     */
    float   sumx2 = 0.0;                     /* sum of x**2  */
    float   sumxy = 0.0;                     /* sum of x * y */
    float   sumy = 0.0;                      /* sum of y     */
    float   sumy2 = 0.0;                     /* sum of y**2  */

    for (int i=0;i<n;i++){ 
        sumx  += x[i];       
        sumx2 += x[i]*x[i];  
        sumxy += x[i]*y[i];
        sumy  += y[i];      
        sumy2 += y[i]*y[i]; 
    } 

    float denom = (n * sumx2 - sumx*sumx);
    if (denom == 0) {
        // singular matrix. can't solve the problem.
        *m = 0;
        *b = 0;
        if (r) *r = 0;
            return 'E';
    }

    *m = (n * sumxy  -  sumx * sumy) / denom;
    *b = (sumy * sumx2  -  sumx * sumxy) / denom;
    if (r!=NULL) {
        *r = (sumxy - sumx * sumy / n) /    /* compute correlation coeff */
              sqrt((sumx2 - (sumx*sumx)/n) *
              (sumy2 - (sumy*sumy)/n));
    }

    return 'D'; 
}
