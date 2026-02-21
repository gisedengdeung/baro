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
  // 이름 입력을 위한 props 추가
  newZoneName,
  onNameChange,
}) {
  return (
    <div className="zone-config">
      <div className="zone-config-header">
        <h3>위험 구역 관리</h3>
        <button className="btn-cancel" onClick={onCancel}>취소</button>
      </div>
      <div className="zone-config-buttons">
        <button
          className={currentAction === 'view' ? 'active' : ''}
          onClick={() => onActionSelect('view')}
        >조회</button>
        <button
          className={currentAction === 'create' ? 'active' : ''}
          onClick={() => onActionSelect('create')}
        >생성</button>
        <button
          disabled={!selected}
          className={currentAction === 'update' ? 'active' : ''}
          onClick={() => onActionSelect('update')}
        >업데이트</button>
        <button
          disabled={!selected}
          onClick={onDelete} // 올바른 삭제 함수를 직접 호출하도록 수정
        >삭제</button>
      </div>

      {/* '생성' 모드일 때 이름 입력 및 안내 필드 표시 */}
      {currentAction === 'create' && (
        <div className="zone-name-input-container guidance-box">
          <p className="guidance-title">새 위험 구역 생성</p>
          <p className="guidance-step">1. 먼저 구역 이름을 입력하세요.</p>
          <input
            type="text"
            id="zoneName"
            placeholder="예: 1번 컨베이어 벨트"
            value={newZoneName}
            onChange={(e) => onNameChange(e.target.value)}
            autoFocus
          />
          <p className="guidance-step">2. 다음, 왼쪽 화면에서 마우스로 위험 구역을 클릭하여 그리세요. 완료되면 자동으로 저장됩니다.</p>
        </div>
      )}

      <ul className="zone-list">
        {zones.length === 0 ? (
          <li className="empty">등록된 위험 구역이 없습니다.</li>
        ) : (
          zones.map(z => (
            <li
              key={z.id}
              className={z.id === selected ? 'selected' : ''}
              onClick={() => onSelect(z.id)}
            >
              {z.name || `Zone ${z.id}`}
            </li>
          ))
        )}
      </ul>
    </div>
  );
}