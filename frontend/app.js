/* Vue 3 UI for the procurement agent.  Kept as a CDN entry so the Python
   service can serve the project without a Node build step. */
const { createApp, ref, computed, onMounted, onBeforeUnmount, nextTick } = Vue;

const ChartPanel = {
    props: { chart: { type: Object, required: true } },
    template: '<div class="chart-panel" style="height:250px;width:100%"></div>',
    mounted() { this.draw(); },
    watch: { chart: { deep: true, handler() { this.draw(); } } },
    methods: {
        draw() {
            if (!window.echarts) return;
            nextTick(() => {
                const instance = echarts.init(this.$el);
                const entries = Object.entries(this.chart.data || {});
                const option = {
                    animation: false,
                    color: ['#2d7b82', '#e0a458', '#7a9e9f', '#c87941'],
                    title: { text: this.chart.title || '', left: 0, textStyle: { fontSize: 13, fontWeight: 600, color: '#34454d' } },
                    tooltip: { trigger: this.chart.type === 'pie' ? 'item' : 'axis' },
                    grid: { top: 40, left: 42, right: 18, bottom: 30 },
                };
                if (this.chart.type === 'pie') {
                    option.series = [{ type: 'pie', radius: ['28%', '68%'], data: entries.map(([name, value]) => ({ name, value })) }];
                } else {
                    option.xAxis = { type: 'category', data: entries.map(([name]) => name), axisLabel: { interval: 0, rotate: entries.length > 4 ? 25 : 0, fontSize: 10 } };
                    option.yAxis = { type: 'value', name: this.chart.y_name || '', nameTextStyle: { fontSize: 10 } };
                    option.series = [{ type: this.chart.type, data: entries.map(([, value]) => value), barMaxWidth: 32 }];
                }
                instance.setOption(option, true);
                this._instance = instance;
                window.addEventListener('resize', this.resize);
            });
        },
        resize() { if (this._instance) this._instance.resize(); },
    },
    beforeUnmount() { window.removeEventListener('resize', this.resize); if (this._instance) this._instance.dispose(); },
};

createApp({
    components: { ChartPanel },
    setup() {
        const sessions = ref([]);
        const messages = ref([]);
        const currentThreadId = ref(null);
        const input = ref('');
        const draft = ref('');
        const toolLines = ref([]);
        const streaming = ref(false);
        const interrupt = ref(null);
        const supplement = ref({});
        const tasks = ref([]);
        const artifacts = ref([]);
        const erps = ref([]);
        const subagents = ref([]);
        const selectedTask = ref(null);
        const persistenceBackend = ref('file');
        const approvalStats = ref({ total: 0, pending: 0, approved: 0, rejected: 0, cancelled: 0, response_rate: 0, avg_response_seconds: null });
        let pollTimer = null;

        const selectedCharts = computed(() => selectedTask.value?.result?.charts || []);

        function markdown(value) {
            if (!value) return '';
            const rendered = window.marked ? marked.parse(value) : value.replace(/\n/g, '<br>');
            return window.DOMPurify ? DOMPurify.sanitize(rendered) : rendered;
        }
        function timeText(timestamp) {
            if (!timestamp) return '';
            return new Date(timestamp * 1000).toLocaleString();
        }
        function statusLabel(status) {
            return ({ queued: '排队中', running: '执行中', completed: '已完成', failed: '失败' }[status] || status || '未知');
        }
        function parseSSE(raw) {
            if (!raw || !raw.trim()) return null;
            let eventType = 'message';
            const data = [];
            raw.split(/\r?\n/).forEach(line => {
                if (line.startsWith('event:')) eventType = line.slice(6).trim();
                if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
            });
            if (!data.length) return null;
            try { return { eventType, data: JSON.parse(data.join('\n')) }; } catch (_) { return null; }
        }
        async function consume(response, handler) {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split(/\r?\n\r?\n/);
                buffer = events.pop() || '';
                events.map(parseSSE).filter(Boolean).forEach(handler);
            }
            const finalEvent = parseSSE(buffer);
            if (finalEvent) handler(finalEvent);
        }
        function handleEvent(event) {
            const data = event.data || {};
            const type = data.type || event.eventType;
            if (data.thread_id) currentThreadId.value = data.thread_id;
            if (type === 'token') draft.value += data.content || '';
            if (type === 'tool_start') toolLines.value.push(`调用 ${data.tool || '工具'}...`);
            if (type === 'tool_result') {
                toolLines.value.push(`${data.tool || '工具'} 已返回`);
                try {
                    const result = typeof data.content === 'string' ? JSON.parse(data.content) : data.content;
                    if (result?.task_id) refreshTasks();
                } catch (_) { /* 工具结果不一定是 JSON */ }
            }
            if (type === 'interrupt') {
                interrupt.value = data;
                supplement.value = {};
            }
            if (type === 'error') ElementPlus.ElMessage.error(data.message || '服务调用失败');
        }
        function finishStream(interrupted) {
            if (!interrupted && draft.value.trim()) messages.value.push({ role: 'assistant', content: draft.value });
            draft.value = '';
            streaming.value = false;
            loadSessions();
        }
        async function sendMessage() {
            const text = input.value.trim();
            if (!text || streaming.value) return;
            input.value = '';
            messages.value.push({ role: 'user', content: text });
            draft.value = '';
            toolLines.value = [];
            streaming.value = true;
            try {
                const payload = { message: text, user_id: 'default_user', username: '用户' };
                if (currentThreadId.value) payload.thread_id = currentThreadId.value;
                const response = await fetch('/api/chat/stream', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                let interrupted = false;
                await consume(response, event => { handleEvent(event); if ((event.data || {}).interrupted) interrupted = true; });
                finishStream(interrupted || !!interrupt.value);
            } catch (error) {
                streaming.value = false;
                ElementPlus.ElMessage.error(error.message || '发送失败');
            }
        }
        async function resume(payload) {
            if (!currentThreadId.value || streaming.value) return;
            streaming.value = true;
            draft.value = '';
            try {
                const response = await fetch(`/api/chat/${currentThreadId.value}/resume`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ resume: payload }),
                });
                let interrupted = false;
                await consume(response, event => { handleEvent(event); if ((event.data || {}).interrupted) interrupted = true; });
                if (!interrupted) interrupt.value = null;
                finishStream(interrupted);
            } catch (error) {
                streaming.value = false;
                ElementPlus.ElMessage.error(error.message || '恢复执行失败');
            }
        }
        function approve() { resume({ decisions: [{ type: 'approve' }] }); }
        function reject() { resume({ decisions: [{ type: 'reject' }] }); }
        function cancel() { resume({ decisions: [{ type: 'cancel' }] }); }
        function submitSupplement() {
            resume({ supplement: { ...supplement.value } });
        }
        function quick(text) { input.value = text; sendMessage(); }
        function newChat() { currentThreadId.value = null; messages.value = []; interrupt.value = null; toolLines.value = []; draft.value = ''; }
        async function loadSessions() {
            const response = await fetch('/api/history/sessions?user_id=default_user');
            const data = await response.json(); sessions.value = data.data || [];
        }
        async function loadSession(threadId) {
            const response = await fetch(`/api/history/${threadId}/messages`);
            const data = await response.json();
            currentThreadId.value = threadId;
            messages.value = data.data || [];
            interrupt.value = null;
        }
        async function refreshTasks() {
            const response = await fetch('/api/tasks?user_id=default_user');
            const data = await response.json(); tasks.value = data.data || [];
            if (selectedTask.value) {
                const current = tasks.value.find(task => task.task_id === selectedTask.value.task_id);
                if (current) selectedTask.value = current;
            } else if (tasks.value.length) selectedTask.value = tasks.value[0];
        }
        async function selectTask(task) {
            const response = await fetch(`/api/tasks/${task.task_id}`);
            selectedTask.value = await response.json();
        }
        async function loadArtifacts() {
            const response = await fetch('/api/artifacts?user_id=default_user');
            const data = await response.json(); artifacts.value = data.data || [];
        }
        async function loadApprovalStats() {
            const response = await fetch('/api/approvals/stats?user_id=default_user');
            const data = await response.json();
            if (data.code === 0) approvalStats.value = data.data || approvalStats.value;
        }
        async function loadMeta() {
            const [health, erpResponse, agentResponse] = await Promise.all([
                fetch('/api/health').then(response => response.json()),
                fetch('/api/erps').then(response => response.json()),
                fetch('/api/subagents').then(response => response.json()),
            ]);
            persistenceBackend.value = health.persistence_backend || 'file';
            erps.value = erpResponse.data || [];
            subagents.value = agentResponse.data || [];
        }
        onMounted(async () => {
            try { await Promise.all([loadSessions(), refreshTasks(), loadArtifacts(), loadApprovalStats(), loadMeta()]); } catch (error) { console.warn(error); }
            pollTimer = setInterval(() => { refreshTasks(); loadArtifacts(); loadApprovalStats(); }, 2200);
        });
        onBeforeUnmount(() => clearInterval(pollTimer));

        return {
            sessions, messages, currentThreadId, input, draft, toolLines, streaming, interrupt, supplement,
            tasks, artifacts, erps, subagents, selectedTask, selectedCharts, persistenceBackend, approvalStats,
            markdown, timeText, statusLabel, sendMessage, resume, approve, reject, submitSupplement,
            quick, newChat, loadSession, selectTask, cancel,
        };
    },
    template: `
      <div class="shell">
        <header class="topbar">
          <div class="brand"><span class="brand-mark">采</span><span>智能采购助手</span></div>
          <div class="top-meta"><span class="status-dot"></span><span>服务在线 · {{ persistenceBackend }} 持久化</span></div>
        </header>
        <main class="layout">
          <aside class="sidebar">
            <div class="sidebar-head"><h2 class="sidebar-title">会话</h2><el-button size="small" plain @click="newChat">新建</el-button></div>
            <div class="session-list">
              <button v-for="session in sessions" :key="session.thread_id" class="session" :class="{active: session.thread_id === currentThreadId}" @click="loadSession(session.thread_id)">
                <span class="session-title">{{ session.last_message || '新对话' }}</span><span class="session-time">{{ timeText(session.updated_at) }}</span>
              </button>
              <div v-if="!sessions.length" class="empty">还没有历史会话</div>
            </div>
          </aside>
          <section class="chat">
            <div class="chat-head"><div><h1>采购协作台</h1><p>供应商、物料、订单、分析报告和多 ERP 快照</p></div><el-tag size="small" type="info">LangGraph</el-tag></div>
            <div class="messages">
              <div v-if="!messages.length && !draft" class="message assistant"><div class="bubble">你好，我可以查询采购数据、生成分析报告，也能在订单写入前发起人工审批。</div></div>
              <div v-for="(message, index) in messages" :key="index" class="message" :class="message.role === 'user' ? 'user' : 'assistant'"><div class="bubble" v-html="markdown(message.content)"></div></div>
              <div v-if="toolLines.length" class="tool-line">{{ toolLines.join('  ·  ') }}</div>
              <div v-if="draft" class="message assistant"><div class="bubble" v-html="markdown(draft)"></div></div>
              <div v-if="streaming && !draft" class="message assistant"><div class="bubble">正在处理请求...</div></div>
              <div v-if="interrupt" class="interrupt">
                <h3>{{ interrupt.interrupt_type === 'hitl_approval' ? '订单人工审批' : '需要补充信息' }}</h3>
                <p>{{ interrupt.data?.message || '请确认后继续执行。' }}</p>
                <div v-if="interrupt.interrupt_type === 'order_info_supplement'" v-for="field in (interrupt.data?.missing_fields || [])" :key="field" style="margin:8px 0"><el-input v-model="supplement[field]" :placeholder="field"></el-input></div>
                <pre v-else>{{ JSON.stringify(interrupt.data, null, 2) }}</pre>
                <div class="interrupt-actions"><el-button v-if="interrupt.interrupt_type === 'hitl_approval'" type="success" size="small" @click="approve">批准写入</el-button><el-button v-if="interrupt.interrupt_type === 'hitl_approval'" type="danger" plain size="small" @click="reject">拒绝</el-button><el-button v-if="interrupt.interrupt_type === 'hitl_approval'" type="info" plain size="small" @click="cancel">取消审批</el-button><el-button v-else type="primary" size="small" @click="submitSupplement">提交补充</el-button></div>
              </div>
            </div>
            <div class="input-dock">
              <div class="quick-row"><button @click="quick('查询刹车片的供应商有哪些')">供应商查询</button><button @click="quick('分析制动系统物料的当前价格并生成报告')">价格分析</button><button @click="quick('创建一个采购订单，采购100套前刹车片')">创建订单</button><button @click="quick('列出三个虚拟 ERP 并对比制动系统库存')">多 ERP 对比</button></div>
              <div class="composer"><el-input v-model="input" type="textarea" :autosize="{minRows:1,maxRows:4}" placeholder="输入采购需求，Enter 发送" @keydown.enter.exact.prevent="sendMessage"></el-input><el-button type="primary" :loading="streaming" @click="sendMessage">发送</el-button></div>
            </div>
          </section>
          <aside class="inspector">
            <div class="inspector-section"><div class="panel-head"><h2 class="panel-title">人工审批统计</h2><el-tag size="small" type="warning">HITL</el-tag></div><div class="approval-metrics"><div class="approval-metric"><strong>{{ approvalStats.total }}</strong><span>触发总数</span></div><div class="approval-metric"><strong>{{ approvalStats.pending }}</strong><span>待处理</span></div><div class="approval-metric"><strong>{{ approvalStats.approved }}</strong><span>已批准</span></div><div class="approval-metric"><strong>{{ approvalStats.rejected }}</strong><span>已拒绝</span></div><div class="approval-metric"><strong>{{ approvalStats.cancelled }}</strong><span>已取消</span></div></div><div class="approval-note">处理率 {{ approvalStats.response_rate }}%<span v-if="approvalStats.avg_response_seconds !== null"> · 平均响应 {{ approvalStats.avg_response_seconds }} 秒</span></div></div>
            <div class="inspector-section"><div class="panel-head"><h2 class="panel-title">后台任务</h2><el-tag size="small">{{ tasks.length }}</el-tag></div><div v-for="task in tasks" :key="task.task_id" class="task-item" @click="selectTask(task)"><div class="task-name"><strong>{{ task.task_type }}</strong><span>{{ statusLabel(task.status) }}</span></div><el-progress :percentage="task.progress || 0" :show-text="false" :stroke-width="5"></el-progress><div class="task-stage">{{ task.stage }} · {{ task.task_id }}</div></div><div v-if="!tasks.length" class="empty">暂无异步任务</div></div>
            <div class="inspector-section" v-if="selectedTask?.result"><div class="panel-head"><h2 class="panel-title">分析结果</h2><el-tag size="small" type="success">已完成</el-tag></div><div class="report" v-html="markdown(selectedTask.result.report)"></div><ChartPanel v-for="(chart, index) in selectedCharts" :key="index" :chart="chart"></ChartPanel></div>
            <div class="inspector-section"><div class="panel-head"><h2 class="panel-title">报告与附件</h2><span class="section-caption">可下载</span></div><div v-for="artifact in artifacts" :key="artifact.artifact_id" class="artifact-item"><a :href="artifact.download_url" target="_blank">{{ artifact.name }}</a><br><small>{{ artifact.kind }} · {{ timeText(artifact.created_at) }}</small></div><div v-if="!artifacts.length" class="empty">暂无附件</div></div>
            <div class="inspector-section"><div class="panel-head"><h2 class="panel-title">运行资源</h2></div><div class="section-caption">虚拟 ERP</div><div v-for="erp in erps" :key="erp.id" class="erp-item"><strong>{{ erp.name }}</strong><br><small>{{ erp.id }} · {{ erp.region }} · {{ erp.status }}</small></div><div class="section-caption">子 Agent</div><div v-for="agent in subagents" :key="agent.name" class="erp-item"><strong>{{ agent.name }}</strong><br><small>{{ agent.execution_mode }} · {{ agent.tools.length }} 个配置工具</small></div></div>
          </aside>
        </main>
      </div>
    `,
}).use(ElementPlus).mount('#app');
