# Systems Design Playbook
## الأنماط الأساسية
- Load Balancer (L4/L7)، Reverse Proxy
- Caching: CDN، Cache تطبيق (Redis)
- Message Queue: RabbitMQ/Kafka للفصل بين الخدمات
- Storage: SQL مقابل NoSQL، Sharding/Replication/Read Replicas
- Consistency: CAP, Eventual Consistency, Idempotency
- Observability: Logs, Metrics, Traces (OpenTelemetry)

## واجهات API
- Versioning: /v1, /v2
- Pagination/Filtering
- Rate Limiting, Auth (JWT/OAuth2), RBAC

## قابلية التوسع
- Scale Up vs Scale Out
- Stateless services + Sticky Sessions فقط عند الحاجة
