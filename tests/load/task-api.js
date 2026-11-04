// task-api 负载测试
// 正常模式：2 -> 5 -> 10 iterations/s 三级递增，每级 3 分钟
// 故障模式（MODE=write）：固定 VU 持续写请求，用于验证 5xx 告警
//
// 用法：
//   k6 run -e BASE_URL=http://127.0.0.1:18000 tests/load/task-api.js
//   k6 run -e MODE=write -e DURATION=13m ... tests/load/task-api.js

import http from 'k6/http';
import { check } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = (__ENV.BASE_URL || 'http://127.0.0.1:18000').replace(/\/$/, '');
const WRITE_ONLY = (__ENV.MODE || 'load') === 'write';

const JSON_HEADERS = { headers: { 'Content-Type': 'application/json' } };

const createDuration = new Trend('create_duration', true);
const listDuration = new Trend('list_duration', true);
const deleteDuration = new Trend('delete_duration', true);
const iterationFailed = new Rate('iteration_failed');

export const options = WRITE_ONLY
  ? {
      scenarios: {
        write_fault: {
          executor: 'constant-arrival-rate',
          rate: Number(__ENV.RATE || 2),
          timeUnit: '1s',
          duration: __ENV.DURATION || '13m',
          preAllocatedVUs: 5,
          maxVUs: 20,
          gracefulStop: '10s',
        },
      },
      summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
    }
  : {
      scenarios: {
        mixed: {
          executor: 'ramping-arrival-rate',
          startRate: 1,
          timeUnit: '1s',
          preAllocatedVUs: 10,
          maxVUs: 40,
          stages: [
            { duration: '1m', target: 2 },
            { duration: '3m', target: 2 },
            { duration: '1m', target: 5 },
            { duration: '3m', target: 5 },
            { duration: '1m', target: 10 },
            { duration: '3m', target: 10 },
            { duration: '30s', target: 0 },
          ],
        },
      },
      thresholds: {
        http_req_failed: ['rate<0.01'],
        http_req_duration: ['p(95)<1000', 'p(99)<2000'],
        checks: ['rate>0.99'],
        iteration_failed: ['rate<0.01'],
      },
      summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
    };

export default function () {
  const title = `k6-${__VU}-${__ITER}-${Date.now()}`;
  let taskId = null;

  const createRes = http.post(
    `${BASE_URL}/tasks`,
    JSON.stringify({ title }),
    { ...JSON_HEADERS, tags: { endpoint: 'create' } },
  );
  createDuration.add(createRes.timings.duration);
  const created = check(createRes, { 'create 201': (r) => r.status === 201 });
  if (created) {
    taskId = createRes.json('id');
  }

  if (!WRITE_ONLY) {
    const listRes = http.get(`${BASE_URL}/tasks`, { tags: { endpoint: 'list' } });
    listDuration.add(listRes.timings.duration);
    check(listRes, { 'list 200': (r) => r.status === 200 });
  }

  if (taskId !== null) {
    const deleteRes = http.del(`${BASE_URL}/tasks/${taskId}`, null, {
      tags: { endpoint: 'delete' },
    });
    deleteDuration.add(deleteRes.timings.duration);
    check(deleteRes, { 'delete 204': (r) => r.status === 204 });
  }

  iterationFailed.add(!created);
}
