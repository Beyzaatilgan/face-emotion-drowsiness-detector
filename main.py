"""
problem tanimi: web cam ile insan yüzünü alalım duygu tanima: mutlu, nort, sasirmis

"""
# import libraries
import cv2 # opencv
import mediapipe as mp
import numpy as np

# yardimci fonksiyonlarin tanimlanmasi

# mediapipe face mesh modulunu baslat
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode = False,
                                  max_num_faces = 1,
                                  refine_landmarks = True,
                                  min_detection_confidence = 0.5,
                                  min_tracking_confidence = 0.5)

# opencv ile kamera baslat
cap = cv2.VideoCapture(0)

# yüz meshinden kullanılacak onemli landmark indexlerini al
LEFT_EYE = [159, 145] # ust ve alt goz kapagı
MOUTH = [13, 14] # ust ve alt dudak
MOUTH_LEFT_RIGHT = [69, 291] # dudagin solu ve sagi
LEFT_BROW = [65, 158] # kas ile goz arasi
LEFT_EYE_EAR  = [159, 158, 157, 145, 144, 163, 33, 133] #Sol göz: üst(159, 158, 157), alt(145, 144, 163), sol(33), sağ(133)
RIGHT_EYE_EAR = [386, 385, 384, 374, 373, 380, 362, 263] #Sağ göz: üst(386, 385, 384), alt(374, 373, 380), sol(362), sağ(263)

# Uyku uyarisi için sayac ve esik deger
EAR_THRESHOLD = 0.20      # bu degerin altinda göz kapali sayilir
CLOSED_FRAME_LIMIT = 5    # kac frame kapali kalirsa uyari verilir
closed_frame_count = 0    # kapali frame sayaci

def calculate_ear(landmarks, eye_indices, image_width, image_height):
    def get_point(index):
        lm = landmarks[index]
        return np.array([lm.x * image_width, lm.y * image_height])
     
    # Dikey noktalar (3 çift)
    p2 = get_point(eye_indices[0])
    p3 = get_point(eye_indices[1])
    p4 = get_point(eye_indices[2])
    p5 = get_point(eye_indices[3])
    p6 = get_point(eye_indices[4])
    p7 = get_point(eye_indices[5])
    # Yatay noktalar
    p1 = get_point(eye_indices[6])
    p8 = get_point(eye_indices[7])

    vertical1 = np.linalg.norm(p2 - p6)
    vertical2 = np.linalg.norm(p3 - p5)
    vertical3 = np.linalg.norm(p4 - p7)
    horizontal = np.linalg.norm(p1 - p8)

    ear = (vertical1 + vertical2 + vertical3) / (3.0 * horizontal)
    return ear


# goz acikligi ve agiz acikligi metriklerine gore duygu belirle

def detect_emotion(landmarks, image_width, image_height):

    def get_point(index):
        lm = landmarks[index]
        return np.array([int(lm.x*image_width), int(lm.y*image_height)])

    # kas ve goz noktalari (sol taraf)
    brow_point = get_point(65)
    eye_point = get_point(159)
    brow_lift = np.linalg.norm(brow_point-eye_point)

    #dudak sag ve sol noktalari 
    mouth_left = get_point(61)
    mouth_right = get_point(291)
    mouth_width = np.linalg.norm(mouth_left-mouth_right)

    if brow_lift > 25:
        return "sakin"
    elif mouth_width > 60:
        return "mutlu"
    else:
        return "notr"
    
def draw_sleep_warning(frame):
    """Ekranın üzerine yarı saydam kırmızı uyku uyarısı çizer."""
    overlay = frame.copy()
    h, w, _ = frame.shape

    # Yarı saydam kırmızı dikdörtgen (üst bant)
    cv2.rectangle(overlay, (0, 0), (w, 90), (0, 0, 200), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    # Uyarı metni
    cv2.putText(frame, "⚠ UYKU UYARISI! GOZLER KAPALI",
                (w // 2 - 310, 58),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)    
    


# web cam uzerinden duygu tanima
while True:
    success, frame = cap.read()
    if not success:
        break

    #goruntuyu rgbye cevir bunu mediapipe için yapıyoruz
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    #ekran boyutları
    h, w, _ = frame.shape

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:

            # ----- UYKU TESPİTİ -----
            left_ear  = calculate_ear(face_landmarks.landmark, LEFT_EYE_EAR,  w, h)
            right_ear = calculate_ear(face_landmarks.landmark, RIGHT_EYE_EAR, w, h)
            avg_ear   = (left_ear + right_ear) / 2.0

            if avg_ear < EAR_THRESHOLD:
                closed_frame_count += 1
            else:
                closed_frame_count = 0   # goz acilinca sayaci sifirla

            if closed_frame_count >= CLOSED_FRAME_LIMIT:
                draw_sleep_warning(frame)

            # EAR degerini sol alt koseye yaz (debug icin)
            cv2.putText(frame, f"EAR: {avg_ear:.2f}", (10, h - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

            #duyguyu tespit et
            emotion = detect_emotion(face_landmarks.landmark, w, h)

            # ekrana yaz
            cv2.putText(frame, f"duygu: {emotion}", (30,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            # yuz mesh noktalarini çizdir
            mp.solutions.drawing_utils.draw_landmarks(
                frame, 
                face_landmarks,
                mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec = None,
                connection_drawing_spec = mp.solutions.drawing_utils.DrawingSpec(color=(0,255,0), thickness = 1)

            )

    else:
        # Yüz görünmüyorsa sayacı sıfırla
        closed_frame_count = 0

    cv2.imshow("canli mimik ve duygu takibi", frame)

    if cv2.waitKey(10) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()