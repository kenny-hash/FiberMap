import React, { useEffect, useMemo, useState } from 'react';
import ReactDOM from 'react-dom/client';
import './styles.css';

type Device = {
  id: number;
  cluster_id: number;
  ip: string;
  type: 'switch' | 'host' | 'storage';
  protocol: 'ssh' | 'telnet';
  port: number;
  username?: string | null;
  password?: string | null;
  name?: string | null;
};

type Topology = {
  nodes: Array<{ id: string; label: string; type: Device['type']; ip: string }>;
  links: Array<{ source: string; target: string; source_port?: string; target_port?: string; evidence: string }>;
};

const apiBase = import.meta.env.VITE_API_BASE ?? '';

function App() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [topology, setTopology] = useState<Topology>({ nodes: [], links: [] });
  const [message, setMessage] = useState('准备就绪');
  const [editing, setEditing] = useState<Record<number, string>>({});

  async function refresh() {
    const [deviceResponse, topologyResponse] = await Promise.all([
      fetch(`${apiBase}/api/devices`),
      fetch(`${apiBase}/api/topology`),
    ]);
    setDevices(await deviceResponse.json());
    setTopology(await topologyResponse.json());
  }

  useEffect(() => {
    refresh().catch((error: Error) => setMessage(`加载失败：${error.message}`));
  }, []);

  const deviceById = useMemo(() => new Map(devices.map((device) => [String(device.id), device])), [devices]);

  async function importInventory(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    const response = await fetch(`${apiBase}/api/devices/import`, { method: 'POST', body: form });
    const result = await response.json();
    setMessage(`导入完成：新增 ${result.imported}，更新 ${result.updated}，错误 ${result.errors.length}`);
    await refresh();
  }

  async function updateName(device: Device) {
    const nextName = editing[device.id] ?? device.name ?? '';
    const response = await fetch(`${apiBase}/api/devices/${device.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: nextName }),
    });
    if (!response.ok) {
      setMessage('RFID / 名称更新失败');
      return;
    }
    setMessage(`已更新 ${device.ip} 的 RFID / 名称`);
    await refresh();
  }

  async function createSnapshot() {
    const response = await fetch(`${apiBase}/api/snapshots`, { method: 'POST' });
    const result = await response.json();
    setMessage(`已创建快照 #${result.id}，新增节点 ${result.diff.added_nodes.length}`);
  }

  return (
    <main>
      <header className="hero">
        <div>
          <p className="eyebrow">FiberMap MVP</p>
          <h1>资产视角业务网络拓扑</h1>
          <p>导入交换机、计算服务器、存储服务器清单，基于采集证据生成可追溯拓扑快照。</p>
        </div>
        <div className="actions">
          <label className="button">
            导入 CSV / Excel
            <input type="file" accept=".csv,.xlsx,.xls" onChange={importInventory} />
          </label>
          <a className="button secondary" href={`${apiBase}/api/devices/export`}>导出设备</a>
          <button onClick={createSnapshot}>保存快照</button>
        </div>
      </header>

      <section className="status">{message}</section>

      <section className="grid">
        <article className="card wide">
          <h2>设备清单</h2>
          <table>
            <thead>
              <tr>
                <th>IP</th>
                <th>类型</th>
                <th>协议</th>
                <th>端口</th>
                <th>RFID / 名称</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((device) => (
                <tr key={device.id}>
                  <td>{device.ip}</td>
                  <td><span className={`pill ${device.type}`}>{device.type}</span></td>
                  <td>{device.protocol}</td>
                  <td>{device.port}</td>
                  <td>
                    <input
                      value={editing[device.id] ?? device.name ?? ''}
                      placeholder="可后续补录 RFID"
                      onChange={(event) => setEditing({ ...editing, [device.id]: event.target.value })}
                    />
                  </td>
                  <td><button className="small" onClick={() => updateName(device)}>保存</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="card">
          <h2>拓扑摘要</h2>
          <div className="metrics">
            <strong>{topology.nodes.length}</strong><span>节点</span>
            <strong>{topology.links.length}</strong><span>链路</span>
          </div>
          <div className="canvas">
            {topology.nodes.map((node, index) => (
              <div className={`node ${node.type}`} key={node.id} style={{ top: `${20 + index * 58}px` }}>
                <strong>{node.label}</strong><small>{node.ip}</small>
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <h2>链路证据</h2>
          <ul className="links">
            {topology.links.map((link, index) => (
              <li key={`${link.source}-${link.target}-${index}`}>
                <strong>{deviceById.get(link.source)?.name ?? link.source}</strong>
                <span>{link.source_port} ⇄ {link.target_port}</span>
                <strong>{deviceById.get(link.target)?.name ?? link.target}</strong>
                <em>{link.evidence}</em>
              </li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(<App />);
