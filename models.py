from pydantic import BaseModel, Field

class DetectivePrompt(BaseModel):
    response : str = Field(..., description="챗봇의 응답")
    is_end : bool = Field(..., description="대화를 끝내도 괜찮은 상황인지 여부")

class PromptRequirements(BaseModel):
    purpose : str = Field(..., description="프롬프트의 목적")
    aspects : str = Field(..., description="프롬프트의 기능을 유지하기 위한 요소")
    turn : bool = Field(..., description="프롬프트가 멀티 턴인지 여부")
    input : str = Field(..., description="프롬프트의 입력 양식")
    input_content : str = Field(..., description="프롬프트의 입력 내용")
    output : str = Field(..., description="프롬프트의 출력 양식")
    output_content : str = Field(..., description="프롬프트의 출력 내용")
    rules : str = Field(..., description="프롬프트의 규칙이나 제한사항")

class PromptRequirementsSummary(BaseModel):
    reasoning : str = Field(..., description="요약을 진행하면서 떠오르는 생각과 인사이트")
    summary : str = Field(..., description="요약 내용")
    requirements : PromptRequirements = Field(..., description="요약된 프롬프트의 요구사항")

