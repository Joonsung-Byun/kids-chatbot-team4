"""
Agent 히스토리 출력 테스트
"""
from services.agent_service import run_agent

print("\n🧪 Agent 히스토리 출력 테스트 시작\n")

# 테스트 1: 첫 메시지
print("\n" + "="*80)
print("테스트 1: 감정 표현")
print("="*80)
result1 = run_agent("안녕", "test-123", [])
print(f"\n✅ 응답: {result1['answer']}\n")

# 테스트 2: 위치 정보 없는 질문
print("\n" + "="*80)
print("테스트 2: 위치 정보 없는 질문")
print("="*80)
result2 = run_agent("놀이터 찾아줘", "test-123", result1["conversation_history"])
print(f"\n✅ 응답: {result2['answer']}\n")

# 테스트 3: 위치 정보 있는 질문 (Mock RAG)
print("\n" + "="*80)
print("테스트 3: 위치 정보 있는 질문")
print("="*80)
result3 = run_agent("강남 놀이터 찾아줘", "test-123", result2["conversation_history"])
print(f"\n✅ 응답: {result3['answer']}\n")

print("\n🎉 테스트 완료!\n")
