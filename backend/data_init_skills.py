#!/usr/bin/env python3
"""
Initialize skills data for the RPG system
"""
import asyncio
from sqlalchemy import select, func
from config.database import AsyncSessionLocal
from models.skill import Skill, SkillRankEnum, SkillTypeEnum, TargetTypeEnum

async def init_skills_data():
    """Initialize basic skills"""
    # Initialize database first to create tables
    from config.database import init_db
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # Check if skills already exist
        existing_skills = await session.execute(select(func.count(Skill.id)))
        if existing_skills.scalar() > 0:
            print("Skills already exist, skipping initialization")
            return
        
        # Attack Skills
        attack_skills = [
            Skill(
                name="Мощный удар",
                description="Наносит увеличенный урон противнику",
                rank=SkillRankEnum.E,
                skill_type=SkillTypeEnum.attack,
                target_type=TargetTypeEnum.enemy,
                mana_cost=15,
                cooldown=2,
                level_required=1,
                damage_multiplier=1.3,
                status_effect="Усиленная атака"
            ),
            Skill(
                name="Критический удар",
                description="Высокий шанс критического попадания",
                rank=SkillRankEnum.D,
                skill_type=SkillTypeEnum.attack,
                target_type=TargetTypeEnum.enemy,
                mana_cost=20,
                cooldown=3,
                level_required=5,
                damage_multiplier=1.2,
                status_effect="Увеличенный шанс крита"
            ),
            Skill(
                name="Удар молнии",
                description="Мощная магическая атака",
                rank=SkillRankEnum.C,
                skill_type=SkillTypeEnum.attack,
                target_type=TargetTypeEnum.enemy,
                mana_cost=30,
                cooldown=4,
                level_required=10,
                damage_multiplier=1.8,
                status_effect="Магический урон"
            ),
            Skill(
                name="Огненный шар",
                description="Взрывная атака огнём",
                rank=SkillRankEnum.B,
                skill_type=SkillTypeEnum.attack,
                target_type=TargetTypeEnum.enemy,
                mana_cost=40,
                cooldown=5,
                level_required=20,
                damage_multiplier=2.2,
                status_effect="Поджог"
            )
        ]
        
        # Healing Skills
        healing_skills = [
            Skill(
                name="Малое лечение",
                description="Восстанавливает небольшое количество HP",
                rank=SkillRankEnum.E,
                skill_type=SkillTypeEnum.heal,
                target_type=TargetTypeEnum.self_target,
                mana_cost=10,
                cooldown=1,
                level_required=1,
                heal_amount=30,
                status_effect="Быстрое восстановление"
            ),
            Skill(
                name="Лечение",
                description="Восстанавливает умеренное количество HP",
                rank=SkillRankEnum.D,
                skill_type=SkillTypeEnum.heal,
                target_type=TargetTypeEnum.self_target,
                mana_cost=20,
                cooldown=2,
                level_required=3,
                heal_amount=60,
                status_effect="Регенерация"
            ),
            Skill(
                name="Великое лечение",
                description="Мощное восстановление здоровья",
                rank=SkillRankEnum.C,
                skill_type=SkillTypeEnum.heal,
                target_type=TargetTypeEnum.self_target,
                mana_cost=35,
                cooldown=3,
                level_required=8,
                heal_amount=120,
                status_effect="Сильная регенерация"
            )
        ]
        
        # Buff Skills
        buff_skills = [
            Skill(
                name="Боевая ярость",
                description="Временно увеличивает урон",
                rank=SkillRankEnum.E,
                skill_type=SkillTypeEnum.buff,
                target_type=TargetTypeEnum.self_target,
                mana_cost=15,
                cooldown=5,
                level_required=2,
                damage_multiplier=1.2,
                effect_duration=3,
                status_effect="Увеличенный урон на 3 раунда"
            ),
            Skill(
                name="Каменная кожа",
                description="Временно увеличивает защиту",
                rank=SkillRankEnum.D,
                skill_type=SkillTypeEnum.buff,
                target_type=TargetTypeEnum.self_target,
                mana_cost=20,
                cooldown=6,
                level_required=4,
                defense_multiplier=1.3,
                effect_duration=4,
                status_effect="Увеличенная защита на 4 раунда"
            ),
            Skill(
                name="Благословение",
                description="Комплексное усиление характеристик",
                rank=SkillRankEnum.C,
                skill_type=SkillTypeEnum.buff,
                target_type=TargetTypeEnum.self_target,
                mana_cost=40,
                cooldown=8,
                level_required=12,
                damage_multiplier=1.15,
                defense_multiplier=1.15,
                effect_duration=5,
                status_effect="Благословение: +15% ко всем характеристикам"
            )
        ]
        
        # Defense Skills
        defense_skills = [
            Skill(
                name="Блок",
                description="Увеличивает шанс блокирования атак",
                rank=SkillRankEnum.E,
                skill_type=SkillTypeEnum.defense,
                target_type=TargetTypeEnum.self_target,
                mana_cost=10,
                cooldown=2,
                level_required=1,
                defense_multiplier=1.5,
                status_effect="Защитная стойка"
            ),
            Skill(
                name="Железная защита",
                description="Мощная защитная техника",
                rank=SkillRankEnum.D,
                skill_type=SkillTypeEnum.defense,
                target_type=TargetTypeEnum.self_target,
                mana_cost=25,
                cooldown=4,
                level_required=6,
                defense_multiplier=2.0,
                effect_duration=2,
                status_effect="Железная защита на 2 раунда"
            )
        ]
        
        # Debuff Skills
        debuff_skills = [
            Skill(
                name="Ослабление",
                description="Снижает урон противника",
                rank=SkillRankEnum.E,
                skill_type=SkillTypeEnum.debuff,
                target_type=TargetTypeEnum.enemy,
                mana_cost=15,
                cooldown=3,
                level_required=3,
                damage_multiplier=0.8,
                effect_duration=3,
                status_effect="Ослаблен: -20% урона на 3 раунда"
            ),
            Skill(
                name="Проклятие",
                description="Серьёзное ослабление противника",
                rank=SkillRankEnum.C,
                skill_type=SkillTypeEnum.debuff,
                target_type=TargetTypeEnum.enemy,
                mana_cost=30,
                cooldown=5,
                level_required=15,
                damage_multiplier=0.7,
                defense_multiplier=0.8,
                effect_duration=4,
                status_effect="Проклят: -30% урона, -20% защиты"
            )
        ]
        
        # Add all skills
        all_skills = attack_skills + healing_skills + buff_skills + defense_skills + debuff_skills
        
        for skill in all_skills:
            session.add(skill)
        
        await session.commit()
        print(f"Added {len(all_skills)} skills to the database")

if __name__ == "__main__":
    asyncio.run(init_skills_data())