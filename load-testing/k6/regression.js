// k6 回归测试脚本（在回归注入期间运行）
// k6 Regression Test Script (run during regression injection)

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// 自定义指标 / Custom Metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');

// 测试配置（更高的负载以观察回归影响）
// Test Configuration (higher load to observe regression impact)
export const options = {
  stages: [
    { duration: '30s', target: 20 },  // 预热：增加到20个VU / Warm-up: ramp up to 20 VUs
    { duration: '3m', target: 20 },   // 稳定：保持20个VU运行3分钟 / Stable: maintain 20 VUs for 3 minutes
    { duration: '30s', target: 0 },   // 冷却 / Cool-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000', 'p(99)<5000'], // 放宽阈值以观察回归 / Relaxed thresholds to observe regression
    errors: ['rate<0.10'], // 允许更高的错误率 / Allow higher error rate
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // 测试数据获取端点（会触发DB回归）
  // Test data retrieval endpoint (triggers DB regression)
  let dataRes = http.get(`${BASE_URL}/api/data`);
  let dataCheck = check(dataRes, {
    'data endpoint status is 200': (r) => r.status === 200,
  });
  
  errorRate.add(!dataCheck);
  apiLatency.add(dataRes.timings.duration);

  // 测试任务处理端点（会触发CPU和依赖回归）
  // Test task processing endpoint (triggers CPU and dependency regression)
  const taskPayload = JSON.stringify({
    task_id: `task_${__VU}_${__ITER}`,
    data: { test: 'regression', timestamp: Date.now() }
  });
  
  let processRes = http.post(`${BASE_URL}/api/process`, taskPayload, {
    headers: { 'Content-Type': 'application/json' },
    timeout: '10s', // 增加超时时间以观察依赖回归 / Increase timeout to observe dependency regression
  });
  
  let processCheck = check(processRes, {
    'process endpoint status is 200': (r) => r.status === 200,
  });
  
  errorRate.add(!processCheck);
  apiLatency.add(processRes.timings.duration);

  // 更短的请求间隔（更高的负载）
  // Shorter request interval (higher load)
  sleep(0.5);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  return `
  ====================
  回归测试摘要 / Regression Test Summary
  ====================
  总请求数 / Total Requests: ${data.metrics.http_reqs.values.count}
  平均响应时间 / Avg Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
  P95延迟 / P95 Latency: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
  P99延迟 / P99 Latency: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms
  错误率 / Error Rate: ${(data.metrics.errors.values.rate * 100).toFixed(2)}%
  ====================
  `;
}
