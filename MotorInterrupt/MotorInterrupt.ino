volatile long counterA = 0;
volatile long counterB = 0;
long target = 0;
char motor;
byte MotorAPin1 = 7;
byte MotorAPin2 = 8;
byte MotorBPin1 = 9;
byte MotorBPin2 = 10;
byte InterruptPinA = 2;
byte InterruptPinB = 3;
byte MotorPinState = 15; //This is meant to store all motor pin states. Bit 1 and 2 are Motor A pin one and 2, 3 and 4 are Motor B pin 1 and 2

void setup()
{
  pinMode(MotorAPin1, OUTPUT);
  pinMode(MotorAPin2, OUTPUT);
  pinMode(MotorBPin1, OUTPUT);
  pinMode(MotorBPin2, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(InterruptPinA), countA, RISING);
  attachInterrupt(digitalPinToInterrupt(InterruptPinB), countB, CHANGE);
  Serial.begin(115200);
  Serial.setTimeout(1);
}

void loop()
{ 
  if(Serial.available()) {
    process_line();
    if (target != 0) move_to(motor, &target);
  }
}
  
void process_line() {
  char cmd = Serial.read();
  while (!Serial.available()) {
    delay(1);
  }
  //if(cmd>'Z') cmd-=32;
  switch(cmd) {
    case 'X': motor = Serial.read(); target = Serial.parseInt(); break;
  }
  Serial.print(cmd);
  Serial.print(motor);
  Serial.println(target);
}
  
void move_to(char motor_id, long* target_pos) {
  Serial.print("Moving motor "); Serial.print(motor); Serial.print(" to "); Serial.println(*target_pos);
  long last_difference;
  long difference = 100;
  int not_moved = 0;
  volatile long* counter;
  byte MotorPin1;
  byte MotorPin2;
  byte PinStateShift;
  switch (motor) {
      case 'A': counter = &counterA; MotorPin1 = MotorAPin1; MotorPin2 = MotorAPin2; PinStateShift = 0; break;
      case 'B': counter = &counterB; MotorPin1 = MotorBPin1; MotorPin2 = MotorBPin2; PinStateShift = 2; break;
      default: Serial.print("Invalid motor ID: "); Serial.println(motor); return;
    }
  while (difference != 0) {
    difference = *counter - *target_pos;
    if (difference == last_difference) {
      not_moved += 1;
      if (not_moved > 10000) {
        Serial.print("Motor might be blocked. Stopping. ");
        Serial.print(MotorPinState);
        Serial.println(difference);
        not_moved = 0;
        break;
      }
    } else {
      not_moved = 0;
    }
    if (difference > 0) {
      if ((MotorPinState>>PinStateShift&1) != 1 || (MotorPinState>>PinStateShift&2) != 0) {
        digitalWrite(MotorPin1, HIGH);
        digitalWrite(MotorPin2, LOW);
        MotorPinState |= 1<<PinStateShift;
        MotorPinState &= ~(1 << PinStateShift+1);
      }
    }
    else {
      if ((MotorPinState>>PinStateShift&1) != 0 || (MotorPinState>>PinStateShift&2) != 2) {
        digitalWrite(MotorPin1, LOW);
        digitalWrite(MotorPin2, HIGH);
        MotorPinState |= 1<<PinStateShift+1;
        MotorPinState &= ~(1 << PinStateShift);
      }
    }
    last_difference = difference;
  }
  digitalWrite(MotorPin1, HIGH);
  digitalWrite(MotorPin2, HIGH);
  MotorPinState |= 1<<PinStateShift+1;
  MotorPinState |= 1<<PinStateShift;
  Serial.print("Done "); Serial.print(MotorPinState); Serial.println(*counter);
}

void countA()
{
  if ((MotorPinState&1) == 1 && (MotorPinState&2) == 0) {
    counterA -= 1;
  } else if ((MotorPinState&1) == 0 && (MotorPinState&2) == 2) {
    counterA += 1;
  }
}

void countB()
{
  if ((MotorPinState&4) == 4 && (MotorPinState&8) == 0) {
    counterB -= 1;
  } else if ((MotorPinState&4) == 0 && (MotorPinState&8) == 8) {
    counterB += 1;
  }
}
