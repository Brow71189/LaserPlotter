volatile long counterA = 0;
volatile long counterB = 0;
long target = 0;
char motor;
int not_moved = 0;
float speedA = 378.21; // in steps per second
float speedB = 2.0*11.71; // in steps per second
byte PWMA = 127;
byte PWMB = 127;
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
const byte InterruptPinA = 2;
const byte InterruptPinB = 3;
const byte PWMPinA = 10;
const byte PWMPinB = 11;
const byte SensorPinA = 4;
const byte SensorPinB = 5;
byte verbosity = 1; //0: Only send necessary status messages, 1: Also send information, 2: show debug info

void setup()
{
  pinMode(MotorAPin1, OUTPUT);
  pinMode(MotorAPin2, OUTPUT);
  pinMode(MotorBPin1, OUTPUT);
  pinMode(MotorBPin2, OUTPUT);
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
  Serial.begin(115200);
  Serial.setTimeout(100);
}

void loop()
{ 
  //delay(500);
  if(Serial.available()) {
    process_line();
    if (target != 0) {
      char res = move_to(motor, &target);
      target = 0;
      Serial.write(res);
    }
  }
}
  
void process_line() {
  char cmd = Serial.read();
  char motor_id;
  //if(cmd>'Z') cmd-=32;
  switch(cmd) {
    case 'X': while (!Serial.available()) {
                delay(1);
              }
              motor = Serial.read(); target = Serial.parseInt(); break;
    case 'V': verbosity = Serial.parseInt(); Serial.write(cmd); return;
    case 'R': Serial.write(cmd); return;
    case 'P': while (!Serial.available()) {
                delay(1);
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
	case 'C': while (!Serial.available()) {
		        delay(1);
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
		        delay(1);
	          }
			  char motor_id = Serial.read();
			  switch (motor_id) {
				  case 'A': speedA = Serial.parseFloat(); Serial.write('S'); break;
				  case 'B': speedB = Serial.parseFloat(); Serial.write('S'); break;
				  default: if (verbosity > 0) {
					         Serial.print("Invalid motor ID: "); Serial.println(motor_id);
				           }
						   Serial.write('E'); break;
			  }
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
  long difference = 100;
  long abs_difference;
  volatile long* counter;
  byte MotorPin1;
  byte MotorPin2;
  byte PWMPin;
  byte* PWMValue;
  byte MaxPWMValue;
  byte MinPWMValue;
  float target_speed;
  long brakeThreshold;
  volatile unsigned long* last_time;
  volatile unsigned long* this_time;
  switch (motor_id) {
      case 'A': counter = &counterA; MotorPin1 = MotorAPin1; MotorPin2 = MotorAPin2; PWMPin = PWMPinA; MaxPWMValue = 255; MinPWMValue = 0; brakeThreshold = 400; target_speed = speedA; PWMValue = &PWMA; last_time = &last_timeA; this_time = &this_timeA; break;
      case 'B': counter = &counterB; MotorPin1 = MotorBPin1; MotorPin2 = MotorBPin2; PWMPin = PWMPinB; MaxPWMValue = 255; MinPWMValue = 0; brakeThreshold = 400; target_speed = speedB; PWMValue = &PWMB; last_time = &last_timeB; this_time = &this_timeB; break;
      default: if (verbosity > 0) {
                 Serial.print("Invalid motor ID: "); Serial.println(motor_id);
               }
               return 'E';
    }
  float slope = (float)(MinPWMValue - MaxPWMValue) / brakeThreshold;
  bool first_move = true;
  float current_speed = 0;
  long last_position = *counter;
  long last_loop_time = micros();
  while (difference != 0) {
    long now = micros();
	  long current_position = *counter;
	  difference = current_position - *target_pos;
  	if (last_position != current_position || (now - last_loop_time) > 2.0e6/target_speed ) { // only update speed if counter changed since last time or if more time passed than we would expect for the given speed
      long time_diff = *this_time - *last_time;
      if (time_diff != 0) {
        current_speed = 1.0 / (float)(time_diff) * 1e6;  
      }
  	  if (verbosity > 1) {
        Serial.print("Current speed: "); Serial.print(current_speed); Serial.write(" "); Serial.print(last_position-current_position); Serial.write(" "); Serial.print(*PWMValue); Serial.write(" "); Serial.println(time_diff);
  	  }
  	  if (last_position == current_position) {
        not_moved += 1;
        current_speed = 0;
        if (verbosity > 1) {
          Serial.print("Increasing not moved counter to: "); Serial.println(not_moved);
        }
        if (not_moved > 20) {
          if (verbosity > 0) {
            Serial.print("Motor might be blocked. Stopping. ");
            Serial.println(*counter);
          } else {
            Serial.write('B');
          }
          not_moved = 0;
          break;
          }
        } else {
          not_moved = 0;
        }
	  
	  if ((difference < 0 && (last_position-current_position) > 0) || (difference > 0 && (last_position-current_position) < 0)) {
      current_speed = 0;
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
    //abs_difference = abs(difference); 
    //if (first_move && abs_difference <= brakeThreshold) {
    //  brakeThreshold = abs_difference;
    //  slope = (float)(MinPWMValue - MaxPWMValue) / brakeThreshold;
    //  first_move = false;
    // }
    //if (abs_difference < brakeThreshold) {
    //  PWMValue = (byte) (slope*(brakeThreshold-abs_difference)+MaxPWMValue);
    //} else {
    //  PWMValue = MaxPWMValue;
    //}
    analogWrite(PWMPin, *PWMValue);
	  last_loop_time = now;
	  last_position = current_position;
	}
	
//    last_difference = difference;
  }
  //digitalWrite(MotorPin1, HIGH);
  //digitalWrite(MotorPin2, HIGH);
  *MotorBank |= 1<<MotorPin1;
  *MotorBank |= 1<<MotorPin2;
  if (verbosity > 0) {
    delay(500);
    Serial.print("Done "); Serial.println(*counter);
  }
  //Serial.write(motor_id);
  //Serial.println(*counter);
  return 'X';
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
//  if ((MotorPinState&1) == 1 && (MotorPinState&2) == 0) {
//    counterA -= 1;
//  } else if ((MotorPinState&1) == 0 && (MotorPinState&2) == 2) {
//    counterA += 1;
//  }
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
//  if ((MotorPinState&4) == 4 && (MotorPinState&8) == 0) {
//    counterB -= 1;
//  } else if ((MotorPinState&4) == 0 && (MotorPinState&8) == 8) {
//    counterB += 1;
//  }
}
