### 第一步：构建支持 Dynamo 的镜像

#### 1.1 创建 Dockerfile

```
# Dockerfile
FROM your-registry/your-custom-image:latest

# 安装 Dynamo 依赖
RUN pip install "ai-dynamo[vllm]"

# 确保 transformers 版本兼容
RUN pip install transformers==5.3.0

# 创建启动脚本
COPY dynamo-entrypoint.sh /dynamo-entrypoint.sh
RUN chmod +x /dynamo-entrypoint.sh

# 设置工作目录
WORKDIR /workspace

ENTRYPOINT ["/dynamo-entrypoint.sh"]
```

#### 1.2 创建 Dynamo 启动脚本

```
# dynamo-entrypoint.sh
#!/bin/bash

# 加载环境变量
source /etc/environment

# 设置 GPU 可见性
export CUDA_VISIBLE_DEVICES=all

# 验证 GPU 可用性
python -c "import torch;print(f'GPU count: {torch.cuda.device_count()}')"

# 启动 Dynamo vLLM Worker（替代原来的 vllm serve）
exec python -m dynamo.vllm "$@"
```

#### 1.3 构建镜像

```
# 构建新镜像
docker build -t your-registry/qwen35-397b-dynamo:latest .

# 推送到镜像仓库
docker push your-registry/qwen35-397b-dynamo:latest
```

### 第二步：部署基础设施

#### 2.1 部署 etcd

```
# etcd.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: etcd
  namespace: dynamo-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: etcd
  template:
    metadata:
      labels:
        app: etcd
    spec:
      containers:
      - name: etcd
        image: quay.io/coreos/etcd:v3.5.0
        command:
        - etcd
        - --data-dir=/etcd-data
        - --listen-client-urls=http://0.0.0.0:2379
        - --advertise-client-urls=http://0.0.0.0:2379
        - --listen-peer-urls=http://0.0.0.0:2380
        - --initial-advertise-peer-urls=http://0.0.0.0:2380
        - --initial-cluster=default=http://0.0.0.0:2380
        - --name=default
        ports:
        - containerPort: 2379
        - containerPort: 2380
        volumeMounts:
        - name: etcd-data
          mountPath: /etcd-data
      volumes:
      - name: etcd-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: etcd
  namespace: dynamo-system
spec:
  selector:
    app: etcd
  ports:
  - port: 2379
    targetPort: 2379
    name: client
  - port: 2380
    targetPort: 2380
    name: peer
```

#### 2.2 部署 NATS

```
# nats.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nats
  namespace: dynamo-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nats
  template:
    metadata:
      labels:
        app: nats
    spec:
      containers:
      - name: nats
        image: nats:2.9.0
        args:
        - --jetstream
        - --store_dir=/data
        - --max_memory=1Gi
        - --max_file_store=10Gi
        ports:
        - containerPort: 4222
        - containerPort: 8222
        volumeMounts:
        - name: nats-data
          mountPath: /data
      volumes:
      - name: nats-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: nats
  namespace: dynamo-system
spec:
  selector:
    app: nats
  ports:
  - port: 4222
    targetPort: 4222
    name: client
  - port: 8222
    targetPort: 8222
    name: monitor
```

### 第三步：部署 Dynamo vLLM Workers

#### 3.1 创建 DynamoGraphDeployment

```
# dynamo-qwen35-workers.yaml
apiVersion: nvidia.com/v1alpha1
kind: DynamoGraphDeployment
metadata:
  name: qwen35-397b-workers
  namespace: dynamo-system
spec:
  services:
    Qwen35Worker:
      dynamoNamespace: qwen35-system
      componentType: worker
      replicas: 1  # 根据您的需求调整
      extraPodSpec:
        mainContainer:
          image: your-registry/qwen35-397b-dynamo:latest
          command:
            - /dynamo-entrypoint.sh
          args:
            # 模型路径和配置
            - --model
            - /ppusw/datasets/checkpoints/LLM/qwen/v3.5/Qwen3.5-397B-A17B-INT8
            - --served-model-name
            - Qwen3.5-397B-A17B-INT8
            
            # 并行配置
            - --tensor-parallel-size
            - "8"
            - --distributed-executor-backend
            - mp
            
            # 功能配置
            - --trust-remote-code
            - --enable-auto-tool-choice
            - --tool-call-parser
            - qwen3_coder
            - --enable-prefix-caching
            
            # Dynamo 配置
            - --discovery-backend
            - etcd
            - --port
            - "8000"
            
          resources:
            limits:
              nvidia.com/gpu: 8  # 根据您的 tensor-parallel-size 调整
            requests:
              nvidia.com/gpu: 8
          
          # 挂载模型路径
          volumeMounts:
            - name: model-storage
              mountPath: /ppusw/datasets/checkpoints
              readOnly: true
        
        # 配置存储卷
        volumes:
          - name: model-storage
            hostPath:
              path: /ppusw/datasets/checkpoints
              type: Directory
      
      # 环境变量配置
      envs:
        # Dynamo 基础设施连接
        - name: DYNAMO_ETCD_ENDPOINT
          value: "http://etcd.dynamo-system.svc.cluster.local:2379"
        - name: DYNAMO_NATS_ENDPOINT
          value: "nats://nats.dynamo-system.svc.cluster.local:4222"
        
        # Worker 标识
        - name: DYNAMO_WORKER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        
        # 日志级别
        - name: DYNAMO_LOG_LEVEL
          value: "INFO"
        
        # KV 缓存配置
        - name: DYNAMO_KV_CACHE_ENABLED
          value: "true"
```

### 第四步：部署 Dynamo Frontend

#### 4.1 创建 Frontend 配置

```
# dynamo-frontend.yaml
apiVersion: nvidia.com/v1alpha1
kind: DynamoGraphDeployment
metadata:
  name: dynamo-frontend
  namespace: dynamo-system
spec:
  services:
    Frontend:
      dynamoNamespace: qwen35-system
      componentType: frontend
      replicas: 2  # 高可用配置
      extraPodSpec:
        mainContainer:
          image: nvcr.io/nvidia/ai-dynamo/dynamo-frontend:1.0.0
          ports:
            - containerPort: 8000
              name: http
          resources:
            requests:
              cpu: "1"
              memory: "2Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
      
      envs:
        # 服务配置
        - name: DYN_HTTP_PORT
          value: "8000"
        - name: DYN_HTTP_HOST
          value: "0.0.0.0"
        
        # 路由配置
        - name: DYN_ROUTER_MODE
          value: "kv"  # 启用 KV 感知路由
        - name: DYN_ROUTER_KV_OVERLAP_SCORE_WEIGHT
          value: "1.0"
        - name: DYN_ROUTER_TEMPERATURE
          value: "0.0"
        - name: DYN_ROUTER_RESET_STATES
          value: "true"
        
        # 基础设施连接
        - name: DYNAMO_ETCD_ENDPOINT
          value: "http://etcd.dynamo-system.svc.cluster.local:2379"
        - name: DYNAMO_NATS_ENDPOINT
          value: "nats://nats.dynamo-system.svc.cluster.local:4222"
        
        # 日志和监控
        - name: DYNAMO_LOG_LEVEL
          value: "INFO"
        - name: DYN_METRICS_ENABLED
          value: "true"
        
        # 超时配置
        - name: DYN_REQUEST_TIMEOUT
          value: "300"
        - name: DYN_HEALTH_CHECK_INTERVAL
          value: "30"

---
# Frontend Service
apiVersion: v1
kind: Service
metadata:
  name: dynamo-frontend
  namespace: dynamo-system
spec:
  selector:
    nvidia.com/dynamo-component-name: Frontend
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  type: LoadBalancer  # 或根据需要改为 NodePort/ClusterIP
```

### 第五步：部署步骤

#### 5.1 创建命名空间

```
# 创建 Dynamo 系统命名空间
kubectl create namespace dynamo-system
```

#### 5.2 按顺序部署

```
# 1. 部署基础设施
kubectl apply -f etcd.yaml
kubectl apply -f nats.yaml

# 2. 等待基础设施就绪
kubectl wait --for=condition=available --timeout=300s deployment/etcd -n dynamo-system
kubectl wait --for=condition=available --timeout=300s deployment/nats -n dynamo-system

# 3. 部署 vLLM Workers
kubectl apply -f dynamo-qwen35-workers.yaml

# 4. 等待 Workers 就绪
kubectl wait --for=condition=ready --timeout=600s pod -l nvidia.com/dynamo-component-name=Qwen35Worker -n dynamo-system

# 5. 部署 Frontend
kubectl apply -f dynamo-frontend.yaml

# 6. 等待 Frontend 就绪
kubectl wait --for=condition=ready --timeout=300s pod -l nvidia.com/dynamo-component-name=Frontend -n dynamo-system
```

### 第六步：验证和测试

#### 6.1 检查部署状态

```
# 检查所有 Pod 状态
kubectl get pods -n dynamo-system

# 检查 DynamoGraphDeployment 状态
kubectl get dynamographdeployment -n dynamo-system

# 查看 Frontend 日志
kubectl logs -n dynamo-system -l nvidia.com/dynamo-component-name=Frontend

# 查看 Worker 日志
kubectl logs -n dynamo-system -l nvidia.com/dynamo-component-name=Qwen35Worker
```

#### 6.2 测试 API 连接

```
# 获取 Frontend 服务地址
kubectl get svc dynamo-frontend -n dynamo-system

# 端口转发（用于测试）
kubectl port-forward -n dynamo-system svc/dynamo-frontend 8000:8000 &

# 测试模型列表
curl http://localhost:8000/v1/models

# 测试聊天完成
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen3.5-397B-A17B-INT8",
    "messages": [
      {"role": "user", "content": "请写一个 Python 函数计算斐波那契数列"}
    ],
    "max_tokens": 200,
    "temperature": 0.7
  }'
```

#### 6.3 测试 KV 感知路由

```
# 发送第一个请求
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen3.5-397B-A17B-INT8",
    "messages": [{"role": "user", "content": "def fibonacci(n):"}],
    "max_tokens": 100
  }'

# 发送相似前缀的请求，应该路由到同一个 worker
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen3.5-397B-A17B-INT8", 
    "messages": [{"role": "user", "content": "def fibonacci(n): # 计算第n个斐波那契数"}],
    "max_tokens": 100
  }'
```

### 第七步：监控和调优

#### 7.1 查看 KV 缓存状态

```
# 查看 etcd 中的 worker 注册信息
kubectl exec -n dynamo-system deployment/etcd -- etcdctl get --prefix /dynamo/workers

# 查看 NATS 中的消息流
kubectl port-forward -n dynamo-system svc/nats 8222:8222 &
curl http://localhost:8222/streaming
```

#### 7.2 性能调优参数

```
# 在 Frontend 环境变量中添加调优参数
envs:
  # 路由策略调优
  - name: DYN_ROUTER_KV_OVERLAP_THRESHOLD
    value: "0.5"  # KV 重叠阈值
  - name: DYN_ROUTER_LOAD_BALANCE_WEIGHT
    value: "0.3"  # 负载均衡权重
  
  # 缓存管理
  - name: DYN_KV_CACHE_TTL
    value: "3600"  # KV 缓存 TTL（秒）
  - name: DYN_KV_CACHE_MAX_SIZE
    value: "10000"  # 最大缓存条目数
  
  # 连接池配置
  - name: DYN_CONNECTION_POOL_SIZE
    value: "100"
  - name: DYN_REQUEST_QUEUE_SIZE
    value: "1000"
```

### 故障排查

#### 常见问题和解