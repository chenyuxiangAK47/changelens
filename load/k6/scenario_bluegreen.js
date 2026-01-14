/**
 * ChangeLens k6 Blue-Green Deployment Scenario
 * Simulates blue-green deployment with automated rollback
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { Rate } from 'k6/metrics';

// Custom metrics
const checkoutLatency = new Trend('checkout_latency_ms');
const checkoutErrors = new Counter('checkout_errors');
const errorRate = new Rate('error_rate');

// Rollback configuration
const P99_THRESHOLD_MS = parseInt(__ENV.P99_THRESHOLD_MS || '500');
const ERR_THRESHOLD = parseFloat(__ENV.ERR_THRESHOLD || '0.05'); // 5%
const WINDOW_SEC = parseInt(__ENV.WINDOW_SEC || '10');
const CONSEC_WINDOWS = parseInt(__ENV.CONSEC_WINDOWS || '2');

// Service URLs
const API_V1_URL = __ENV.API_V1_URL || 'http://api_v1:8001';
const API_V2_URL = __ENV.API_V2_URL || 'http://api_v2:8001';

// Deployment schedule
const WARMUP_DURATION = 60; // seconds
const BLUEGREEN_SWITCH_TIME = 120; // seconds - switch to v2
const TEST_DURATION = 600; // 10 minutes total

// State tracking
let currentVersion = 'v1'; // Start with v1
let rollbackTriggered = false;
let windowStartTime = Date.now();
let windowLatencies = [];
let windowErrors = 0;
let windowRequests = 0;
let consecutiveBadWindows = 0;

export const options = {
    stages: [
        { duration: `${WARMUP_DURATION}s`, target: 10 },
        { duration: `${TEST_DURATION - WARMUP_DURATION}s`, target: 10 },
    ],
    thresholds: {
        http_req_duration: ['p(99)<2000'],
    },
};

function shouldRollback() {
    if (rollbackTriggered) {
        return true;
    }
    
    const now = Date.now();
    const elapsed = (now - windowStartTime) / 1000;
    
    if (elapsed >= WINDOW_SEC) {
        // Calculate metrics for this window
        if (windowLatencies.length > 0) {
            windowLatencies.sort((a, b) => a - b);
            const p99Index = Math.floor(windowLatencies.length * 0.99);
            const p99 = windowLatencies[p99Index];
            const errorRate = windowErrors / windowRequests;
            
            console.log(`[Window] P99: ${p99.toFixed(2)}ms, Error Rate: ${(errorRate * 100).toFixed(2)}%, Requests: ${windowRequests}`);
            
            if (p99 > P99_THRESHOLD_MS || errorRate > ERR_THRESHOLD) {
                consecutiveBadWindows++;
                console.log(`[Rollback Check] Bad window detected (${consecutiveBadWindows}/${CONSEC_WINDOWS})`);
                
                if (consecutiveBadWindows >= CONSEC_WINDOWS) {
                    rollbackTriggered = true;
                    console.log(`[ROLLBACK TRIGGERED] Switching back to v1`);
                    return true;
                }
            } else {
                consecutiveBadWindows = 0;
            }
        }
        
        // Reset window
        windowStartTime = now;
        windowLatencies = [];
        windowErrors = 0;
        windowRequests = 0;
    }
    
    return rollbackTriggered;
}

function selectVersion(testStartTime) {
    const elapsed = (Date.now() - testStartTime) / 1000;
    
    // Check rollback first
    if (shouldRollback()) {
        return 'v1';
    }
    
    // Blue-Green switch: at BLUEGREEN_SWITCH_TIME, switch to v2
    if (elapsed >= BLUEGREEN_SWITCH_TIME) {
        return 'v2';
    }
    
    return 'v1';
}

export default function () {
    const testStartTime = __VU === 1 ? Date.now() : 0; // Approximate start time
    
    const version = selectVersion(testStartTime);
    const url = version === 'v1' ? API_V1_URL : API_V2_URL;
    
    const user_id = `user_${Math.floor(Math.random() * 1000)}`;
    const amount = Math.random() * 100 + 10;
    
    const payload = JSON.stringify({
        user_id: user_id,
        amount: amount.toFixed(2)
    });
    
    const params = {
        headers: { 'Content-Type': 'application/json' },
        tags: { 
            name: 'checkout',
            version: version,
            deployment: 'bluegreen'
        },
    };
    
    const res = http.post(`${url}/checkout`, payload, params);
    
    const success = check(res, {
        'status is 200': (r) => r.status === 200,
    });
    
    // Track metrics
    windowRequests++;
    if (res.status === 200) {
        try {
            const body = JSON.parse(res.body);
            const latency = body.latency_ms || res.timings.duration;
            checkoutLatency.add(latency);
            windowLatencies.push(latency);
        } catch (e) {
            const latency = res.timings.duration;
            checkoutLatency.add(latency);
            windowLatencies.push(latency);
        }
        errorRate.add(0);
    } else {
        checkoutErrors.add(1);
        windowErrors++;
        errorRate.add(1);
    }
    
    sleep(0.1);
}
