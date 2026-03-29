export default function ConveyorMode({
  className,
  operationMode,
  loading,
  onStartAutomatic,
  onStartMaintenance,
  onStop,
  onDangerMode,
}) {

  const getStatusText = () => {
    if (operationMode === 'AUTOMATIC') return <span style={{color: '#5cb85c', fontWeight: 'bold'}}>운전 모드</span>;
    if (operationMode === 'MAINTENANCE') return <span style={{color: '#337ab7', fontWeight: 'bold'}}>정비 모드</span>;
    if (operationMode === null) return '불러오는 중...';
    return <span style={{color: '#d9534f', fontWeight: 'bold'}}>정지 상태</span>;
  };

  return (
    <div className={`${className} conveyor-mode`}>
      <h3>🛠️ 컨트롤 보드</h3>
      <button 
        onClick={onStartAutomatic} 
        disabled={loading || operationMode === 'AUTOMATIC'}
        className="btn-start"
      >
        {loading && operationMode !== 'AUTOMATIC' ? "⏳ 전환 중..." : "▶️ 운전 모드 시작"}
      </button>
      <button 
        onClick={onStartMaintenance} 
        disabled={loading || operationMode === 'MAINTENANCE'}
        className="btn-maintenance"
      >
        {loading && operationMode !== 'MAINTENANCE' ? "⏳ 전환 중..." : "🛠️ 정비 모드 시작"}
      </button>
      <button
        onClick={onStop}
        disabled={loading || operationMode === 'STOPPED'}
        className="btn-stop"
      >
        {loading && operationMode === 'STOPPED' ? "⏳ 정지 중..." : "⏹️ 시스템 정지"}
      </button>
      <button onClick={onDangerMode} disabled={loading} className="btn-danger-zone">
        ⚠️ 위험 구역 설정
      </button>
      <div className="status-line">
        현재 상태: {getStatusText()}
      </div>
    </div>
  );
}
