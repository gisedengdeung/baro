import React from 'react';
import './ZoneConfigPanel.css';

export default function ZoneConfigPanel({
  zones = [],
  selected,
  onSelect,
  currentAction,
  onActionSelect,
  onDelete,
  onCancel,
  newZoneName,
  onNameChange,
  loading, // 로딩 상태 추가
}) {
  return (
    <div className="zone-config">
      <div className="zone-config-header">
        <h3>위험 구역 관리</h3>
        <button className="btn-cancel" onClick={onCancel}>나가기</button>
      </div>
      <div className="zone-config-buttons">
        <button
          className={currentAction === 'view' ? 'active' : ''}
          onClick={() => onActionSelect('view')}
          disabled={loading}
        >조회</button>
        <button
          className={currentAction === 'create' ? 'active' : ''}
          onClick={() => onActionSelect('create')}
          disabled={loading}
        >추가</button>
        <button
          disabled={!selected || loading}
          className={currentAction === 'update' ? 'active' : ''}
          onClick={() => onActionSelect('update')}
        >수정</button>
        <button
          disabled={!selected || loading}
          onClick={onDelete}
          className="btn-delete"
        >
          {loading && selected ? "⏳ 삭제 중" : "삭제"}
        </button>
      </div>

      {/* '생성' 모드일 때 이름 입력 및 안내 필드 표시 */}
      {currentAction === 'create' && (
        <div className="zone-name-input-container guidance-box">
          <p className="guidance-title">🆕 새 구역 만들기</p>
          <div className="step-item">
            <span className="step-num">1</span>
            <p>구역의 이름을 입력하세요.</p>
          </div>
          <input
            type="text"
            id="zoneName"
            placeholder="예: 컨베이어 A 진입로"
            value={newZoneName}
            onChange={(e) => onNameChange(e.target.value)}
            autoFocus
            disabled={loading}
          />
          <div className="step-item">
            <span className="step-num">2</span>
            <p>왼쪽 영상 화면에서 <strong>마우스로 3번 이상 클릭</strong>하여 영역을 그리세요. 마지막 점을 찍으면 자동 저장됩니다.</p>
          </div>
          {loading && <div className="loading-status">📡 서버로 전송 중...</div>}
        </div>
      )}

      {/* '수정' 모드일 때 안내 */}
      {currentAction === 'update' && (
        <div className="guidance-box update-guidance">
          <p className="guidance-title">✏️ 영역 수정하기</p>
          <div className="step-item">
            <span className="step-num">1</span>
            <p>구역의 이름을 수정할 수 있습니다.</p>
          </div>
          <input
            type="text"
            id="zoneNameUpdate"
            placeholder="구역 이름"
            value={newZoneName}
            onChange={(e) => onNameChange(e.target.value)}
            disabled={loading}
          />
          <div className="step-item">
            <span className="step-num">2</span>
            <p>영상 화면을 다시 클릭하여 새로운 영역을 그리세요. 완료 시 기존 데이터가 덮어씌워집니다.</p>
          </div>
          {loading && <div className="loading-status">📡 업데이트 중...</div>}
        </div>
      )}

      {/* '조회' 모드일 때 안내 */}
      {currentAction === 'view' && (
        <div className="guidance-box view-guidance">
          <p className="guidance-title">🔍 구역 조회</p>
          <p>아래 목록에서 구역을 선택하면 영상 화면에서 해당 영역이 강조됩니다.</p>
        </div>
      )}

      <ul className="zone-list">
        {zones.length === 0 ? (
          <li className="empty">등록된 구역이 없습니다.</li>
        ) : (
          zones.map(z => (
            <li
              key={z.id}
              className={z.id === selected ? 'selected' : ''}
              onClick={() => !loading && onSelect(z.id)}
            >
              {z.name || `Zone ${z.id}`}
            </li>
          ))
        )}
      </ul>
    </div>
  );
}