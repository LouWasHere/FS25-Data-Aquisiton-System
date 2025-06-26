void setup() {
  Serial1.begin(9600);
  delay(100);
}

void loop() {
  //int sensorValue = analogRead(A0);
  Serial1.print("Wheel Speed:12345,Neutral Flag:0,Killswitch:0\n");
  delay(500);
}
`