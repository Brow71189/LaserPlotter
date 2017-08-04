volatile long counter = 0;
long target = 0;
int MotorPin1 = 7;
int MotorPin2 = 8;
byte MotorPinState = 0;

void setup()
{
  pinMode(MotorPin1, OUTPUT);
  pinMode(MotorPin2, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(2), count, RISING);
  Serial.begin(115200);
  //digitalWrite(MotorPin1, MotorPin1State);
  //digitalWrite(MotorPin2, MotorPin2State);
}

void loop()
{ 
  if(Serial.available()) {
    process_line();
    if (target != 0) move_to(target);   
  }
}
  
//  if (counter >= 15050) {
//    digitalWrite(MotorPin1, HIGH);
//    digitalWrite(MotorPin2, HIGH);
//    counter = 0;
//  if (MotorPin1State == 0) {
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

void process_line() {
  char cmd = Serial.read();
  if(cmd>'Z') cmd-=32;
  switch(cmd) {
    case 'X': target = Serial.parseInt();
  }
}
  
void move_to(long target_pos) {
  Serial.print("Moving to "); Serial.println(target_pos);
  long last_difference;
  long difference = 100;
  int not_moved = 0;
  while (difference != 0) {
    difference = counter - target_pos;
    if (difference == last_difference) {
      not_moved += 1;
      if (not_moved > 1000) {
        Serial.print("Motor might be blocked. Stopping. ");
        Serial.println(difference);
        not_moved = 0;
        break;
      }
    } else {
      not_moved = 0;
    }
    if (difference > 0) {
      if (MotorPinState != 1) {
        digitalWrite(MotorPin1, HIGH);
        digitalWrite(MotorPin2, LOW);
        MotorPinState = 1;
      }
    }
    else {
      if (MotorPinState != 2) {
        digitalWrite(MotorPin1, LOW);
        digitalWrite(MotorPin2, HIGH);
        MotorPinState = 2;
      }
    }
    last_difference = difference;
  }
  digitalWrite(MotorPin1, HIGH);
  digitalWrite(MotorPin2, HIGH);
  MotorPinState = 3;
  Serial.print("Done "); Serial.println(counter);
}

void count()
{
  if (MotorPinState == 1) {
    counter -= 1;
  } else if (MotorPinState == 2) {
    counter += 1;
  }
}
