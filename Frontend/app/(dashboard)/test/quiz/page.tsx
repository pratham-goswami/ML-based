"use client"

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/hooks/use-toast'
import { Clock, ChevronLeft, ChevronRight, Save, Loader2 } from 'lucide-react'
import { Progress } from '@/components/ui/progress'
import { mockTestAPI } from '@/lib/api'
import { MockTest, MockTestQuestion } from '@/lib/data'

export default function TestPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const testId = searchParams.get('testId')
  
  const [mockTest, setMockTest] = useState<MockTest | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [timeRemaining, setTimeRemaining] = useState(3600)
  const { toast } = useToast()
  
  // Fetch mock test data
  useEffect(() => {
    const fetchMockTest = async () => {
      if (!testId) {
        toast({
          title: "Error",
          description: "No test ID provided",
          variant: "destructive"
        })
        router.push('/test')
        return
      }

      try {
        const test = await mockTestAPI.getMockTest(testId)
        setMockTest(test)
        setTimeRemaining(test.time_limit * 60) // Convert minutes to seconds
      } catch (error) {
        console.error('Error fetching mock test:', error)
        toast({
          title: "Error",
          description: "Failed to load test",
          variant: "destructive"
        })
        router.push('/test')
      } finally {
        setLoading(false)
      }
    }

    fetchMockTest()
  }, [testId, toast, router])
  
  const question = mockTest?.questions[currentQuestion]
  const progress = mockTest ? Math.round(((currentQuestion + 1) / mockTest.questions.length) * 100) : 0
  
  // Timer effect
  useEffect(() => {
    if (!mockTest || timeRemaining <= 0) return
    
    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          handleSubmit() // Auto-submit when time runs out
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [mockTest, timeRemaining])
  
  const handleAnswer = (answer: string) => {
    if (!question) return
    setAnswers(prev => ({
      ...prev,
      [question.id]: answer
    }))
  }
  
  const handleNext = () => {
    if (mockTest && currentQuestion < mockTest.questions.length - 1) {
      setCurrentQuestion(prev => prev + 1)
    }
  }
  
  const handlePrevious = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(prev => prev - 1)
    }
  }
  
  const handleSubmit = async () => {
    if (!mockTest || submitting) return
    
    setSubmitting(true)
    try {
      const timeTaken = (mockTest.time_limit * 60) - timeRemaining // Calculate time taken
      const result = await mockTestAPI.submitMockTest(mockTest.test_id, answers, timeTaken)
      
      toast({
        title: "Test submitted successfully",
        description: "Your answers have been analyzed."
      })
      
      // Store the analysis result in sessionStorage for the results page
      sessionStorage.setItem('testAnalysis', JSON.stringify(result))
      
      // Navigate to results page
      router.push(`/test/results?testId=${mockTest.test_id}&submissionId=${result.submission_id}`)
    } catch (error) {
      console.error('Error submitting test:', error)
      toast({
        title: "Error",
        description: "Failed to submit test. Please try again.",
        variant: "destructive"
      })
    } finally {
      setSubmitting(false)
    }
  }
  
  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  
  if (loading) {
    return (
      <div className="container mx-auto py-8 px-4 flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p>Loading test...</p>
        </div>
      </div>
    )
  }
  
  if (!mockTest || !question) {
    return (
      <div className="container mx-auto py-8 px-4 text-center">
        <p>Test not found</p>
        <Button onClick={() => router.push('/test')} className="mt-4">
          Back to Tests
        </Button>
      </div>
    )
  }
  
  return (
    <div className="container mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">{mockTest.title}</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-5 w-5" />
            <span className="font-mono">{formatTime(timeRemaining)}</span>
          </div>
          <Button 
            onClick={handleSubmit} 
            className="gap-2"
            disabled={submitting}
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Submit Test
          </Button>
        </div>
      </div>
      
      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex justify-between text-sm text-muted-foreground mb-2">
          <span>Question {currentQuestion + 1} of {mockTest.questions.length}</span>
          <span>{progress}% Complete</span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>
      
      {/* Question card */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-start gap-2">
            <span className="text-muted-foreground">Q{currentQuestion + 1}.</span>
            <span>{question.question}</span>
          </CardTitle>
          <div className="text-sm text-muted-foreground">
            Marks: {question.marks} | Type: {question.type.toUpperCase()}
          </div>
        </CardHeader>
        <CardContent>
          {question.type === 'mcq' ? (
            <RadioGroup
              value={answers[question.id]}
              onValueChange={handleAnswer}
              className="space-y-3"
            >
              {question.options?.map((option: string, index: number) => (
                <div key={index} className="flex items-center space-x-3">
                  <RadioGroupItem value={option} id={`option-${index}`} />
                  <Label htmlFor={`option-${index}`}>{option}</Label>
                </div>
              ))}
            </RadioGroup>
          ) : (
            <Textarea
              value={answers[question.id] || ''}
              onChange={(e) => handleAnswer(e.target.value)}
              placeholder="Type your answer here..."
              className="min-h-[200px]"
            />
          )}
        </CardContent>
      </Card>
      
      {/* Navigation */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={handlePrevious}
          disabled={currentQuestion === 0}
          className="gap-2"
        >
          <ChevronLeft className="h-4 w-4" /> Previous
        </Button>
        <Button
          onClick={handleNext}
          disabled={currentQuestion === mockTest.questions.length - 1}
          className="gap-2"
        >
          Next <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
      
      {/* Question palette */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Question Palette</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-10 gap-2">
            {mockTest.questions.map((q: MockTestQuestion, index: number) => (
              <Button
                key={q.id}
                variant={answers[q.id] ? "default" : "outline"}
                className={`h-10 w-10 p-0 ${currentQuestion === index ? 'ring-2 ring-primary' : ''}`}
                onClick={() => setCurrentQuestion(index)}
              >
                {index + 1}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}