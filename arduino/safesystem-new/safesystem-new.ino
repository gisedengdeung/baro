// 모터 드라이버 제어 핀 (SpeedController용)
const int MOTOR_ENA = 9;
const int MOTOR_IN1 = 8;
const int MOTOR_IN2 = 7;

// 릴레이 모듈 제어 핀 (PowerController용)
/*
 * 릴레이 연결상태 NO, 전원과 릴레이의 상태가 동일
 */
const int RELAY_PIN = 10;

// 피에조 부저 핀 (AlertController용)
const int BUZZER_PIN = 11;

// PIR 센서 핀
const int PIR_PIN = 2;

// PIR 센서 상태
int pir_state = LOW;
int last_pir_state = LOW;

void setup() {
  // 시리얼 통신 시작 (Python과 통신용)
  Serial.begin(9600);

  // 모터 드라이버 핀 초기화
  pinMode(MOTOR_ENA, OUTPUT);
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  digitalWrite(MOTOR_ENA, LOW); // 모터는 기본 비활성화

  // 릴레이 핀 초기화
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); // 릴레이는 기본 OFF 상태

  // 부저 핀 초기화
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW); // 부저는 기본적으로 OFF (LOW 상태)로 시작

  // PIR 센서 핀 초기화
  pinMode(PIR_PIN, INPUT);

  Serial.println("Arduino is ready. control enabled.");
}

// --- 메인 루프 ---
void loop() {
  // 1. Python으로부터 오는 시리얼 명령어 처리
  handle_serial_commands();

  // 2. 센서 데이터 처리
  handle_sensors();
}

// --- 함수 정의 ---

/*
 * @brief Python으로부터 받은 시리얼 명령어를 처리합니다.
 *        - 속도 제어(s), 전원 제어(p), 부저 제어(b) 명령어를 모두 처리합니다.
 */
void handle_serial_commands() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim(); // 혹시 모를 공백 제거

    // PowerController를 위한 전원 제어 명령어 (p0, p1)
    if (cmd.startsWith("p")) {
      int state = cmd.substring(1).toInt();
      if (state == 0) {
        digitalWrite(RELAY_PIN, LOW); // 릴레이 OFF
        digitalWrite(MOTOR_IN1, LOW);
        digitalWrite(MOTOR_IN2, LOW);
        analogWrite(MOTOR_ENA, 0); // 혹시 몰라서 모터도 OFF
        Serial.println("Command: p0 -> Power OFF (Relay LOW) & Motor Stopped");
      } else {
        digitalWrite(RELAY_PIN, HIGH);  // 릴레이 ON
        Serial.println("Command: p1 -> Power ON (Relay HIGH)");
      }
    }
    // SpeedController를 위한 모터 속도 제어 명령어 (s0 ~ s255)
    else if (cmd.startsWith("s")) {
      int pwmVal = cmd.substring(1).toInt();
      if (pwmVal > 0) {
        pwmVal = constrain(pwmVal, 0, 255);
        digitalWrite(RELAY_PIN, HIGH);   // 전원 ON
        digitalWrite(MOTOR_IN1, HIGH);
        digitalWrite(MOTOR_IN2, LOW);
        analogWrite(MOTOR_ENA, pwmVal);
        Serial.print("Command: s -> Speed set to: ");
        Serial.println(pwmVal);
      } else {
        digitalWrite(MOTOR_IN1, LOW);
        digitalWrite(MOTOR_IN2, LOW);
        analogWrite(MOTOR_ENA, 0);
        digitalWrite(RELAY_PIN, LOW);    // 전원 OFF
        Serial.println("Command: s -> Motor stopped");
      }
    }
    // AlertController를 위한 부저 제어 명령어 (b_medium, b_high, b_critical)
    else if (cmd.startsWith("b")) {
      if (cmd.equals("b_medium")) {
        Serial.println("Command: b_medium -> Playing MEDIUM alert sound.");
        play_alert_sound(392); // 낮은 솔 (G4)
      } else if (cmd.equals("b_high")) {
        Serial.println("Command: b_high -> Playing HIGH alert sound.");
        play_alert_sound(523); // 높은 도 (C5)
      } else if (cmd.equals("b_critical")) {
        Serial.println("Command: b_critical -> Playing CRITICAL alert sound.");
        play_alert_sound(784); // 높은 솔 (G5)
      } else if (cmd.equals("b_stop")) {
        Serial.println("Command: b_stop -> Stopping all sounds.");
        noTone(BUZZER_PIN);
      }
    }
  }
}

/*
 * @brief 지정된 주파수로 3번 반복되는 경고음을 재생하고, 확실히 멈춥니다.
 * @param note_frequency 재생할 음의 주파수 (Hz)
 */
void play_alert_sound(int note_frequency) {
  for (int i = 0; i < 9; i++) { // 반복 횟수를 9번으로 늘림
    tone(BUZZER_PIN, note_frequency, 150); // 150ms 동안 소리 재생
    delay(200); // 200ms 쉼
  }
  noTone(BUZZER_PIN); // 함수가 끝나기 전에 부저를 확실히 끕니다.
}

/*
 * @brief 모든 센서의 현재 상태를 읽고, 위험 시 자율적으로 반응합니다.
 */
void handle_sensors() {
  // PIR 센서 상태 읽기
  pir_state = digitalRead(PIR_PIN);

  // 상태가 "감지(0)"로 변경된 경우, 즉시 전원을 차단합니다.
  if (pir_state == 0 && last_pir_state != 0) {
    digitalWrite(RELAY_PIN, LOW);  // 릴레이 OFF
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, 0);  // 혹시 몰라 모터도 정지
    // 자율적으로 전원을 껐다고 PC에 보고합니다.
    Serial.println("{\"type\":\"STATUS\",\"source\":\"AUTO\",\"power\":\"OFF\"}");
  }

  // 상태 변화가 있을 때만 PC로 센서 데이터를 전송합니다.
  if (pir_state != last_pir_state) {
    send_pir_data();
    last_pir_state = pir_state;
  }
}

/*
 * @brief PIR 센서 데이터를 JSON 형식으로 시리얼 포트에 출력합니다.
 */
void send_pir_data() {
  // JSON 형식: {"type": "PIR", "value": 0 또는 1}
  Serial.print("{\"type\": \"PIR\", \"value\": ");
  Serial.print(pir_state);
  Serial.println("}");
}