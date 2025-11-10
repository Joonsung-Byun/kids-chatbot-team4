"""
LangChain Import 디버깅 스크립트
설치된 패키지 버전과 import 가능 여부 확인
"""

print("=" * 60)
print("LangChain 패키지 버전 확인")
print("=" * 60)

# 1. 설치된 패키지 버전 확인
try:
    import langchain
    print(f"✅ langchain 버전: {langchain.__version__}")
except Exception as e:
    print(f"❌ langchain import 실패: {e}")

try:
    import langchain_core
    print(f"✅ langchain_core 버전: {langchain_core.__version__}")
except Exception as e:
    print(f"❌ langchain_core import 실패: {e}")

try:
    import langchain_community
    print(f"✅ langchain_community 버전: {langchain_community.__version__}")
except Exception as e:
    print(f"❌ langchain_community import 실패: {e}")

print("\n" + "=" * 60)
print("Import 경로 테스트")
print("=" * 60)

# 2. langchain.agents 모듈 탐색
try:
    import langchain.agents as agents_module
    print(f"\n✅ langchain.agents 모듈 import 성공")
    print(f"📦 사용 가능한 항목들:")
    available = [item for item in dir(agents_module) if not item.startswith('_')]
    for item in sorted(available)[:20]:  # 처음 20개만
        print(f"   - {item}")
    if len(available) > 20:
        print(f"   ... 외 {len(available) - 20}개 더 있음")
except Exception as e:
    print(f"❌ langchain.agents import 실패: {e}")

# 3. 각 클래스별 import 테스트
print("\n" + "=" * 60)
print("개별 Import 테스트")
print("=" * 60)

tests = [
    ("AgentExecutor (직접)", "from langchain.agents import AgentExecutor"),
    ("create_tool_calling_agent (직접)", "from langchain.agents import create_tool_calling_agent"),
    ("AgentExecutor (agent 모듈)", "from langchain.agents.agent import AgentExecutor"),
    ("AgentExecutor (agent_executor)", "from langchain.agents.agent_executor import AgentExecutor"),
]

for name, import_statement in tests:
    try:
        exec(import_statement)
        print(f"✅ {name}: 성공")
        print(f"   코드: {import_statement}")
    except ImportError as e:
        print(f"❌ {name}: 실패")
        print(f"   코드: {import_statement}")
        print(f"   에러: {e}")
    except Exception as e:
        print(f"⚠️ {name}: 기타 오류")
        print(f"   에러: {e}")
    print()

# 4. 대안 경로 찾기
print("=" * 60)
print("대안 경로 탐색")
print("=" * 60)

try:
    import importlib
    import pkgutil
    
    # langchain.agents 하위 모듈 탐색
    agents_path = importlib.import_module('langchain.agents').__path__
    print(f"\n📁 langchain.agents 하위 모듈:")
    for importer, modname, ispkg in pkgutil.iter_modules(agents_path):
        print(f"   - {modname} {'(패키지)' if ispkg else ''}")
except Exception as e:
    print(f"⚠️ 모듈 탐색 실패: {e}")

print("\n" + "=" * 60)
print("권장 해결 방법")
print("=" * 60)
print("""
현재 설치된 LangChain 버전에 문제가 있을 수 있습니다.

해결 방법 1: 패키지 재설치
  pip uninstall langchain langchain-core langchain-community -y
  pip install langchain==1.0.3 langchain-core==1.0.3 langchain-community==0.4.1

해결 방법 2: 구버전 사용 (안정성 우선)
  pip uninstall langchain langchain-core langchain-community -y
  pip install "langchain<1.0" "langchain-core<1.0"

해결 방법 3: 최신 버전 사용
  pip uninstall langchain langchain-core langchain-community -y
  pip install --upgrade langchain langchain-core langchain-community
""")