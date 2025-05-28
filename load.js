// load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    vus: 1,       // Виртуальные пользователи
    duration: '60s', // Длительность теста
};

export default function () {
    // const res = http.get('http://0.0.0.0:8003');
    const res = http.get('http://localhost:8000/profile/1/full');
    
    check(res, { 'status was 200': (r) => r.status == 200 });
    // sleep(1);
}