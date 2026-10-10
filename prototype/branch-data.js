// Fictional public fixtures. Shared by home previews and complete branch information panels.
// No registration API, real contacts, or actual branch claims are provided.
const facilities = [
  { id: 'strength', title: '웨이트 공간', image: 'gym-strength.png', alt: '덤벨과 벤치가 놓인 가상의 웨이트 운동 공간', description: '덤벨과 벤치, 근력 운동 기구를 살펴볼 수 있는 공간입니다.' },
  { id: 'cardio', title: '유산소 공간', image: 'gym-cardio.png', alt: '창가에 러닝머신과 실내 자전거가 배치된 가상의 유산소 운동 공간', description: '러닝머신과 실내 자전거가 배치된 운동 공간입니다.' },
  { id: 'stretch', title: '스트레칭 공간', image: 'gym-stretch.png', alt: '운동 매트와 폼롤러가 준비된 가상의 스트레칭 공간', description: '운동 전후 스트레칭을 위한 매트와 소도구 공간입니다.' },
];

export const branches = [
  {
    id: 'main', name: 'Y3GYM 본점', label: '본점', address: '서울 ○○구 ○○로 00',
    weekday: '06:00–23:00', weekend: '09:00–18:00', phone: '02-0000-0001', channel: '본점 채널 예시',
    facilityNote: '본점 시설 배치 예시 · 합성 임시 사진', facilities,
    trainers: [{ id: 'a', name: '트레이너 A', image: 'trainer-a.png', alt: '짙은 회색 운동복을 입은 가상의 남성 트레이너', description: '운동을 시작하기 전, 목표와 궁금한 점을 함께 이야기해보세요.' }],
  },
  {
    id: 'second', name: 'Y3GYM 예시점', label: '예시점', address: '경기 ○○시 ○○로 00',
    weekday: '07:00–22:00', weekend: '10:00–18:00', phone: '031-000-0002', channel: '예시점 채널 예시',
    facilityNote: '예시점 시설 배치 예시 · 검수용 합성 사진을 재사용했습니다.', facilities,
    trainers: [{ id: 'b', name: '트레이너 B', image: 'trainer-b.png', alt: '짙은 회색 운동복을 입은 가상의 여성 트레이너', description: '시설 이용과 운동에 관해 궁금한 내용을 편하게 문의하세요.' }],
  },
];
