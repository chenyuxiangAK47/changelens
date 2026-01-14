/**
 * ChangeLens k6 Checkout Load Test Script
 * Base script for checkout endpoint testing
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

// Custom metrics
const checkoutLatency = new Trend('checkout_latency_ms');
const checkoutErrors = new Counter('checkout_errors');

// Configuration
const API_V1_URL = __ENV.API_V1_URL || 'http://localhost:8001';
const API_V2_URL = __ENV.API_V2_URL || 'http://localhost:8001';
const VUS = parseInt(__ENV.VUS || '10');
const DURATION = __ENV.DURATION || '60s';

export const options = {
    stages: [
        { duration: '60s', target: VUS },  // Warm-up
        { duration: DURATION, target: VUS }, // Main test
    ],
    thresholds: {
        http_req_duration: ['p(99)<1000'], // 99% of requests should be below 1s
        http_req_failed: ['rate<0.01'],    // Error rate should be less than 1%
    },
};

export default function () {
    const user_id = `user_${Math.floor(Math.random() * 1000)}`;
    const amount = Math.random() * 100 + 10; // Random amount between 10-110
    
    const payload = JSON.stringify({
        user_id: user_id,
        amount: amount.toFixed(2)
    });
    
    const params = {
        headers: { 'Content-Type': 'application/json' },
        tags: { name: 'checkout' },
    };
    
    // This will be overridden by scenario scripts
    const url = API_V1_URL;
    
    const res = http.post(`${url}/checkout`, payload, params);
    
    const success = check(res, {
        'status is 200': (r) => r.status === 200,
        'response time < 1000ms': (r) => r.timings.duration < 1000,
    });
    
    if (res.status === 200) {
        try {
            const body = JSON.parse(res.body);
            checkoutLatency.add(body.latency_ms || res.timings.duration);
        } catch (e) {
            checkoutLatency.add(res.timings.duration);
        }
    } else {
        checkoutErrors.add(1);
    }
    
    sleep(0.1); // 100ms think time
}
