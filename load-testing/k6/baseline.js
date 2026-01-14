// k6 基线负载测试脚本
// k6 Baseline Load Test Script

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// 自定义指标 / Custom Metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');

// 测试配置 / Test Configuration
export const options = {
  stages: [
    { duration: '30s', target: 10 },   // 预热阶段：30秒内增加到10个VU / Warm-up: ramp up to 10 VUs in 30s
    { duration: '2m', target: 10 },   // 稳定阶段：保持10个VU运行2分钟 / Stable: maintain 10 VUs for 2 minutes
    { duration: '30s', target: 0 },   // 冷却阶段：30秒内减少到0 / Cool-down: ramp down to 0 in 30s
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95%请求<500ms, 99%请求<1000ms
    errors: ['rate<0.05'], // 错误率<5%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // 测试健康检查端点 / Test health check endpoint
  let healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health check status is 200': (r) => r.status === 200,
  });

  // 测试数据获取端点 / Test data retrieval endpoint
  let dataRes = http.get(`${BASE_URL}/api/data`);
  let dataCheck = check(dataRes, {
    'data endpoint status is 200': (r) => r.status === 200,
    'data endpoint has items': (r) => {
      try {
        const items = JSON.parse(r.body);
        return Array.isArray(items) && items.length > 0;
      } catch (e) {
        return false;
      }
    },
  });
  
  errorRate.add(!dataCheck);
  apiLatency.add(dataRes.timings.duration);

  // 测试任务处理端点 / Test task processing endpoint
  const taskPayload = JSON.stringify({
    task_id: `task_${__VU}_${__ITER}`,
    data: { test: 'data', timestamp: Date.now() }
  });
  
  let processRes = http.post(`${BASE_URL}/api/process`, taskPayload, {
    headers: { 'Content-Type': 'application/json' },
  });
  
  let processCheck = check(processRes, {
    'process endpoint status is 200': (r) => r.status === 200,
  });
  
  errorRate.add(!processCheck);
  apiLatency.add(processRes.timings.duration);

  // 请求间隔（模拟真实用户行为）
  // Request interval (simulate real user behavior)
  sleep(1);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  // 简单的文本摘要输出
  // Simple text summary output
  return `
  ====================
  测试摘要 / Test Summary
  ====================
  总请求数 / Total Requests: ${data.metrics.http_reqs.values.count}
  平均响应时间 / Avg Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
  P95延迟 / P95 Latency: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
  P99延迟 / P99 Latency: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms
  错误率 / Error Rate: ${(data.metrics.errors.values.rate * 100).toFixed(2)}%
  ====================
  `;
}
