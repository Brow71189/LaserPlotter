volatile long counterA = 0;
volatile long counterB = 0;
long target = 0;
char motor;
int not_moved = 0;
volatile unsigned char* MotorBank = &PORTB;
volatile unsigned char* SensorBank = &PIND;
byte MotorAPin1 = 8;
byte MotorAPin2 = 9;
byte MotorBPin1 = 12;
byte MotorBPin2 = 13;
const byte InterruptPinA = 2;
const byte InterruptPinB = 3;
const byte PWMPinA = 10;
const byte PWMPinB = 11;
const byte SensorPinA = 4;
const byte SensorPinB = 5;
byte verbosity = 1; //0: Only send necessary status messages, 1: Also send information

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
              char motor_id = Serial.read();
              switch (motor_id) {
                case 'A': Serial.print(counterA); Serial.write('P'); break;
                case 'B': Serial.print(counterB); Serial.write('P'); break;
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
  long last_difference;
  long difference = 100;
  long abs_difference;
  volatile long* counter;
  byte MotorPin1;
  byte MotorPin2;
  byte PWMPin;
  byte PWMValue;
  byte MaxPWMValue;
  byte MinPWMValue;
  long brakeThreshold;
  switch (motor_id) {
      case 'A': counter = &counterA; MotorPin1 = MotorAPin1; MotorPin2 = MotorAPin2; PWMPin = PWMPinA; MaxPWMValue = 100; MinPWMValue = 40; brakeThreshold = 400; break;
      case 'B': counter = &counterB; MotorPin1 = MotorBPin1; MotorPin2 = MotorBPin2; PWMPin = PWMPinB; MaxPWMValue = 175; MinPWMValue = 120; brakeThreshold = 10; break;
      default: if (verbosity > 0) {
                 Serial.print("Invalid motor ID: "); Serial.println(motor_id);
               }
               return 'E';
    }
  float slope = (float)(MinPWMValue - MaxPWMValue) / brakeThreshold;
  bool first_move = true;
  while (difference != 0) {
    difference = *counter - *target_pos;
    if (difference == last_difference) {
      not_moved += 1;
      if (not_moved > 1000) {
        if (verbosity > 0) {
          Serial.print("Motor might be blocked. Stopping. ");
          Serial.println(difference);
        } else {
          Serial.write('B');
        }
        not_moved = 0;
        break;
      }
    } else {
      not_moved = 0;
    }
    if (difference > 0) {
        *MotorBank |= 1<<MotorPin1;
        *MotorBank &= ~(1<<MotorPin2);
    }
    else {
        *MotorBank |= 1<<MotorPin2;
        *MotorBank &= ~(1<<MotorPin1);
    }
    abs_difference = abs(difference); 
    if (first_move && abs_difference <= brakeThreshold) {
      brakeThreshold = abs_difference;
      slope = (float)(MinPWMValue - MaxPWMValue) / brakeThreshold;
      first_move = false;
    }
    if (abs_difference < brakeThreshold) {
      PWMValue = (byte) (slope*(brakeThreshold-abs_difference)+MaxPWMValue);
    } else {
      PWMValue = MaxPWMValue;
    }
    analogWrite(PWMPin, PWMValue);
    last_difference = difference;
  }
  //digitalWrite(MotorPin1, HIGH);
  //digitalWrite(MotorPin2, HIGH);
  *MotorBank |= 1<<MotorPin1;
  *MotorBank |= 1<<MotorPin2;
  if (verbosity > 0) {
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
    counterA--;
  } else {
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
    counterB--;
  } else {
    counterB++;
  }
//  if ((MotorPinState&4) == 4 && (MotorPinState&8) == 0) {
//    counterB -= 1;
//  } else if ((MotorPinState&4) == 0 && (MotorPinState&8) == 8) {
//    counterB += 1;
//  }
}
