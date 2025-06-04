void setup() {
  Serial1.begin(9600);
  delay(100);
}

void loop() {
  //int sensorValue = analogRead(A0);
  Serial1.print("RPM:12345,Speed:67,Gear:3\n");
  delay(500);
}
`