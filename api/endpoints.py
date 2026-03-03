import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List

from schemas import CrawlStartRequest, CrawlJobStatus, CrawlJobResult
from core.manager import CrawlerManager

router = APIRouter(prefix="/crawl", tags=["crawl"])
manager = CrawlerManager()

@router.post("/start", response_model=dict)
async def start_crawl(request: CrawlStartRequest):
    job_id = await manager.start_job(
        seeds=[str(url) for url in request.seeds],
        max_concurrency=request.max_concurrency
    )
    return {"job_id": job_id, "message": "Crawl job started"}

@router.get("/{job_id}/status", response_model=CrawlJobStatus)
async def job_status(job_id: str):
    crawler = manager.get_job(job_id)
    if not crawler:
        raise HTTPException(status_code=404, detail="Job not found")
    task = manager.tasks.get(job_id)
    status = "running"
    if task and task.done():
        status = "completed" if not task.cancelled() and not task.exception() else "failed"
    return CrawlJobStatus(
        job_id=job_id,
        status=status,
        visited_count=len(crawler.visited),
        queue_size=crawler.queue.qsize(),
        output_dir=crawler.output_dir
    )

@router.get("/{job_id}/results", response_model=List[CrawlJobResult])
async def job_results(job_id: str):
    crawler = manager.get_job(job_id)
    if not crawler:
        raise HTTPException(status_code=404, detail="Job not found")
    if not os.path.exists(crawler.output_dir):
        return []
    results = []
    for fname in os.listdir(crawler.output_dir):
        if fname.endswith(".md"):
            results.append(CrawlJobResult(url="unknown", markdown_file=fname))
    return results

@router.get("/{job_id}/file/{filename}")
async def download_file(job_id: str, filename: str):
    crawler = manager.get_job(job_id)
    if not crawler:
        raise HTTPException(status_code=404, detail="Job not found")
    file_path = os.path.join(crawler.output_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="text/markdown", filename=filename)

@router.post("/{job_id}/stop")
async def stop_job(job_id: str):
    crawler = manager.get_job(job_id)
    if not crawler:
        raise HTTPException(status_code=404, detail="Job not found")
    crawler.stop()
    return {"message": "Job stopping"}