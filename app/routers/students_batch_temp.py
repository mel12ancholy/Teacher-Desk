    return {"message": "学生删除成功"}

from fastapi import Request
from urllib.parse import parse_qs
import re

@router.post("/batch")
async def create_students_batch(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    import json
    
    content_type = request.headers.get('content-type', '')
    
    students_list = []
    
    if 'application/json' in content_type:
        body = await request.body()
        body_str = body.decode('utf-8')
        try:
            data = json.loads(body_str)
            students_list = data.get("students", [])
        except:
            pass
    else:
        body = await request.body()
        body_str = body.decode('utf-8')
        
        if '&' in body_str or '=' in body_str:
            parsed = parse_qs(body_str, keep_blank_values=True)
            keys = list(parsed.keys())
            
            indices = set()
            for key in keys:
                match = re.match(r'students\[(\d+)\]', key)
                if match:
                    indices.add(int(match.group(1)))
            
            for i in indices:
                student_dict = {}
                for field in ['name', 'student_no', 'gender', 'phone', 'parent_phone', 'address', 'class_id']:
                    key_patterns = [
                        f'students[{i}][{field}]',
                        f'students[{i}].{field}'
                    ]
                    
                    val = None
                    for k in key_patterns:
                        if k in parsed and parsed[k] and parsed[k][0]:
                            val = parsed[k][0]
                            break
                    
                    if val:
                        if field == 'class_id':
                            try:
                                student_dict[field] = int(val)
                            except:
                                student_dict[field] = None
                        else:
                            student_dict[field] = val
                
                if student_dict.get('name') and student_dict.get('student_no'):
                    students_list.append(student_dict)
    
    if not students_list:
        return {
            "success": 0,
            "failed": 0,
            "names": [],
            "errors": ["没有有效的学生数据"]
        }
    
    class_ids = get_accessible_class_ids(current_user, db)
    
    results = []
    errors = []
    
    for i, student_data in enumerate(students_list):
        if not isinstance(student_data, dict):
            errors.append(f"第{i+1}行: 数据格式错误")
            continue
            
        class_id = student_data.get("class_id")
        if class_id not in class_ids:
            errors.append(f"第{i+1}行: 无权在该班级添加学生")
            continue
        
        existing = db.query(Student).filter(
            Student.student_no == student_data.get("student_no"),
            Student.class_id == class_id
        ).first()
        if existing:
            errors.append(f"第{i+1}行: 学号 {student_data.get('student_no')} 已存在")
            continue
        
        student = Student(
            name=student_data.get("name", ""),
            student_no=student_data.get("student_no", ""),
            gender=student_data.get("gender", "male"),
            phone=student_data.get("phone", ""),
            parent_phone=student_data.get("parent_phone", ""),
            address=student_data.get("address", ""),
            class_id=class_id,
            teacher_id=current_user.id if current_user.role == "teacher" else None
        )
        db.add(student)
        results.append(student_data.get("name", ""))
    
    db.commit()
    
    return {
        "success": len(results),
        "failed": len(errors),
        "names": results,
        "errors": errors
    }
